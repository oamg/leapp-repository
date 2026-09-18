import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.version import matches_source_version
from leapp.libraries.common.gpg import (
    get_path_to_gpg_certs,
    get_pubkeys_from_rpms,
    GPG_PQC_CERTS_SUBFOLDER,
    iter_gpg_keyfiles,
    parse_gpg_key_from_file
)
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import GpgKey, InstalledRPM, MisplacedTrustedGpgKeys, TrustedGpgKeys


def _get_pubkeys_from_pqrmdb():
    # Example output:
    #   rpm -qa --dbpath /usr/lib/pqrpm/lib/sysimage/rpm/
    #   warning: Unsupported version of key: V6
    #   warning: Could not load key gpg-pubkey-05707a62-68e6a1f3
    #   gpg-pubkey-b2973cf6-5dfd1395
    #   gpg-pubkey-05707a62-68e6a1f3
    #
    # warnings are logged to stderr

    pqrpmdb_path = '/usr/lib/pqrpm/lib/sysimage/rpm/'
    try:
        result = run(['rpm', '-qa', '--dbpath', pqrpmdb_path], split=True)
    except CalledProcessError as e:
        raise StopActorExecutionError(
            f'Failed to query pqrpmdb at {pqrpmdb_path} for imported GPG keys',
            details={'details': str(e)}
        )

    keys = []
    for line in result['stdout']:
        parts = line.strip().split('-')
        if (
            not len(parts) == 4
            # there should never be packages other than gpg-pubkey, if they
            # are, it can be considered an error
            or not parts[0] == 'gpg'
            or not parts[1] == 'pubkey'
            or not len(parts[2]) == 8
        ):
            error = 'Failed to parse fingerprint gpg-pubkey package name {}'.format(line)
            api.current_logger().error(error)
            continue

        # let's make it count as rpmdb=True, because it is imported
        keys.append(GpgKey(fingerprint=parts[2], rpmdb=True))
    return keys


def _parse_trusted_keyfiles(include_pqc):
    """
    :rtype: Dict[String, List[GpgKeyInfo]]
    """
    file_to_fps = {}
    for key_file in iter_gpg_keyfiles(include_pqc=include_pqc):
        file_to_fps[key_file] = parse_gpg_key_from_file(key_file)
    return file_to_fps


def _get_pubkeys(installed_rpms, keyfiles_to_fps):
    """
    Get pubkeys from installed rpms and the trusted directory
    """
    pubkeys = get_pubkeys_from_rpms(installed_rpms)
    db_pubkeys = {key.fingerprint for key in pubkeys}

    # no need to guard by version, pqrpm is only on >= 9.7 && < 10.0
    # the pqrpm package owns the pqrmdb
    if has_package(InstalledRPM, 'pqrpm'):
        # deduplicate, leapp Models are not hashable
        pqc_pubkeys = [k for k in _get_pubkeys_from_pqrmdb() if k.fingerprint not in db_pubkeys]
        pubkeys += pqc_pubkeys
        db_pubkeys |= {k.fingerprint for k in pqc_pubkeys}

    for key_file, fps in keyfiles_to_fps.items():
        for fp in fps:
            if fp not in db_pubkeys:
                pubkeys.append(GpgKey(fingerprint=fp, rpmdb=False, filename=key_file))
                db_pubkeys.add(fp)
    return pubkeys


def _get_misplaced_keyfiles(keyfiles_to_infos):
    """
    Get keys incorrectly placed within the truste GPG keys directory
    """
    root_dir = get_path_to_gpg_certs()
    pqc_dir = os.path.join(root_dir, GPG_PQC_CERTS_SUBFOLDER)

    misplaced_pqc = []  # pqc (v6) keys found at the 'root_dir'
    misplaced_classic = []  # non-PQC keys found in the 'pqc_dir'

    def make_model(keyfile, info):
        return GpgKey(
            fingerprint=info.short_keyid,
            rpmdb=False,
            filename=keyfile
        )

    for keyfile, key_infos in keyfiles_to_infos.items():
        if os.path.dirname(keyfile) == pqc_dir:
            misplaced_classic += [
                make_model(keyfile, key) for key in key_infos if not key.is_pqc
            ]
        else:
            # subdirs other than pqc are ignored by the iterator
            misplaced_pqc += [
                make_model(keyfile, key) for key in key_infos if key.is_pqc
            ]

    return misplaced_pqc, misplaced_classic


def process():
    """
    Process keys in RPM DB and the ones in trusted directory to produce a list of trusted keys

    On 9.9 and 9.10 also search for and produce a MisplacedTrustedGpgKeys message with GPG keys
    misplaced in the trusted directory.
    """

    try:
        installed_rpms = next(api.consume(InstalledRPM))
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No InstalledRPM facts'}
        )

    has_sq = matches_source_version('>= 9.9')
    # without sq there is no way to process PQC keys
    keyfiles_to_infos = _parse_trusted_keyfiles(include_pqc=has_sq)

    keyfiles_to_fps = {
        keyfile: [key_info.short_keyid for key_info in infos]
        for keyfile, infos in keyfiles_to_infos.items()
    }
    pubkeys = _get_pubkeys(installed_rpms, keyfiles_to_fps)
    api.produce(TrustedGpgKeys(items=pubkeys))

    if not has_sq:
        return

    misplaced_pqc, misplaced_classic = _get_misplaced_keyfiles(keyfiles_to_infos)
    if misplaced_pqc or misplaced_classic:
        api.produce(
            MisplacedTrustedGpgKeys(
                pqc_keys=misplaced_pqc, classic_keys=misplaced_classic
            )
        )
