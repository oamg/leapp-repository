from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.gpg import get_gpg_fp_from_file, get_pubkeys_from_rpms, iter_gpg_keyfiles
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import GpgKey, InstalledRPM, TrustedGpgKeys


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
        keys += GpgKey(fingerprint=parts[2], rpmdb=True)
    return keys


def _get_pubkeys(installed_rpms):
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

    for key_file in iter_gpg_keyfiles(include_pqc=True):
        fps = get_gpg_fp_from_file(key_file)
        for fp in fps:
            if fp not in db_pubkeys:
                pubkeys.append(GpgKey(fingerprint=fp, rpmdb=False, filename=key_file))
                db_pubkeys.add(fp)
    return pubkeys


def process():
    """
    Process keys in RPM DB and the ones in trusted directory to produce a list of trusted keys
    """

    try:
        installed_rpms = next(api.consume(InstalledRPM))
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No InstalledRPM facts'}
        )
    pubkeys = _get_pubkeys(installed_rpms)
    api.produce(TrustedGpgKeys(items=pubkeys))
