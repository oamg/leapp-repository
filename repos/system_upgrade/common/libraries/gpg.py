import os
from collections import namedtuple

import rpm

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import config
from leapp.libraries.common.config.version import get_target_major_version, matches_source_version
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import GpgKey
from leapp.utils.deprecation import deprecated

GPG_CERTS_FOLDER = 'rpm-gpg'
GPG_PQC_CERTS_SUBFOLDER = 'pqc'

# The version of the gpg-pubkey RPMs is the last 8 characters of the long key
# ID, which is a different part of the fingerprint for each key version:
#
# v4: 567E347AD0044ADE55BA8A5F199E2F91FD431D51
#                                     ^------^
# v6: FCD355B305707A62DA143AB6E422397E50FE8467A2A95343D246D6276AFEDF8F
#             ^------^
_SHORT_KEY_ID_SLICE = {
    '4': slice(32, 40),
    '6': slice(8, 16),
}


class GpgReadError(StopActorExecutionError):
    pass


class GpgParseError(Exception):
    pass


# TODO when (if) some generic way to query rpmdb is added, deprecate this or
# make it a wrapper
def get_gpg_ascii_from_rpmdb(query_name, db_path=None):
    """
    Get the ascii armor of GPG key(s) imported in rpm DB

    :return: List of ascii armors for the matched packages matching `query_name`
    :rtype: List[str]
    :raises ValueError: If `query_name` does not begin with gpg-pubkey
    :raises rpm.error: Propagates any rpm errors
    """
    if not query_name.startswith('gpg-pubkey'):
        raise ValueError('Only gpg-pubkey packages are allowed')

    # this branching db_path is not nice, but it's the cleanest way to use the
    # default db without hardocoding it or getting it through
    # rpm.expandMacro('%{_dbpath}')
    if db_path:
        rpm.addMacro('_dbpath', db_path)
    try:
        ts = rpm.TransactionSet()
        if db_path:  # TODO
            ts.openDB()
        matched = ts.dbMatch('name', query_name)
    finally:
        # this is global, make sure we unset it
        if db_path:
            rpm.delMacro('_dbpath')

    return [hdr[rpm.RPMTAG_DESCRIPTION] for hdr in matched]


@deprecated(since='2026-11-09', message=(
    'The Model returned by this function has been deprecated.'
    ' Use `get_gpg_ascii_from_rpmdb()` and `parse_gpg_key_from_ascii()` instead.'
))
def get_pubkeys_from_rpms(installed_rpms):
    """
    Return the list of fingerprints of GPG keys in RPM DB

    This function returns short 8 characters fingerprints of trusted GPG keys
    "installed" in the source OS RPM database. These look like normal packages
    named "gpg-pubkey" and the fingerprint is present in the version field.

    :param installed_rpms: List of installed RPMs
    :type installed_rpms: list(leapp.models.RPM)
    :return: list of GPG keys from RPM DB
    :rtype: list(leapp.models.GpgKey)
    """
    return [GpgKey(fingerprint=pkg.version, rpmdb=True) for pkg in installed_rpms.items if pkg.name == 'gpg-pubkey']


def _parse_fps_from_gpg(stdout):
    """
    Parse the output of 'gpg2 --show-keys --with-colons'.

    The output is colon-delimited with one record per line; the record type is
    the first field. A primary key opens with a 'pub:' record and its full
    40-character fingerprint is in the 10th field of the 'fpr:' record that
    follows it, e.g.:

    .. code-block:: text

        pub:-:4096:1:199E2F91FD431D51:1256212795:::-:::scSC::::::23::0:
        fpr:::::::::567E347AD0044ADE55BA8A5F199E2F91FD431D51:

    Only the fingerprint of the primary key is reported. A 'sub:' record opens a
    subkey section, so any 'fpr:' after it (up to the next 'pub:') is ignored;
    this also means a primary key with no 'fpr:' of its own is skipped rather
    than adopting a subkey's fingerprint. The subkeys are part of the primary
    key as an underlying mechanism, so they don't need to be extracted
    separately.

    :param output: Result of running 'gpg2 --show-keys --with-colons'
    :type output: dict
    :return: Lowercased 40-character fingerprints of the primary keys in the
        output, or an empty list when the output is empty or holds no parseable
        fingerprint of a primary key
    :rtype: list(str)
    """
    if not stdout:
        return []

    gpg_fps = []
    in_primary = False  # True while inside a 'pub:' section
    for line in stdout:
        if not line:
            continue
        if line.startswith('pub:'):
            in_primary = True
            continue
        if line.startswith('sub:'):
            in_primary = False
            continue
        if not in_primary or not line.startswith('fpr:'):
            # skip 'uid:'/other records and any 'fpr:' belonging to a subkey
            continue

        # extract fingerprint from the fpr record
        parts = line.split(':')
        if len(parts) >= 10 and len(parts[9]) == 40:
            gpg_fps.append(parts[9].lower())
        else:
            api.current_logger().error(
                'Cannot parse the gpg2 output. Line: "{}"'.format(line)
            )

    return gpg_fps


GpgKeyInfo = namedtuple('GpgKeyInfo', ('fingerprint', 'short_keyid', 'is_pqc'))


def _parse_gpg_key_gpg2(stdin):
    """
    Return the list of public keys read from the given stdin using 'gpg2'

    All the keys are reported as v4 keys. gpg2 cannot read v6 (PQC) keys at
    all, so such keys are skipped with a warning instead of being reported.

    :param stdin: Open file descriptor of a file with GPG key(s), or their ascii armor
    :type stdin: int or str
    :return: List of the public keys read from the given stdin
    :rtype: List[GpgKeyInfo]
    :raises GpgReadError: When gpg2 cannot be executed or exits with an error
    """
    try:
        cmd = ['gpg2', '--show-keys', '--with-colons']
        output = run(cmd, split=True, stdin=stdin)
    except (OSError, CalledProcessError) as err:
        # NOTE: OSError this is hypothetic; gnupg2 has to be installed on RHEL 7+
        error = f'Failed to read fingerprint from GPG key: {str(err)}'
        raise GpgReadError(error) from err

    # hardcode is_pqc=False because gpg2 cannot parse v6 keys so no pqc
    keys = [
        GpgKeyInfo(
            fingerprint=fp,
            short_keyid=fp[_SHORT_KEY_ID_SLICE['4']],
            is_pqc=False
        )
        for fp in _parse_fps_from_gpg(output['stdout'])
    ]

    if not keys:
        api.current_logger().warning(
            'Unable to parse OpenPGP keys: {}'.format(output.get('stderr', ''))
        )
    return keys


def _iter_sq_packets(dump):
    """
    Split the output of 'sq packet dump' into single packets

    Yield the (header, body lines) tuple for every packet in the output. Packet
    headers are the only lines without a leading whitespace, e.g.:

        Public-Key Packet, old CTB, 525 bytes
            Version: 4
            ...

    :param dump: Lines of the 'sq packet dump' output
    :type dump: list(str)
    """
    header = None
    body = []
    for line in dump:
        if line and not line[0].isspace():
            if header is not None:
                yield header, body
            header, body = line, []
        else:
            body.append(line)

    if header is not None:
        yield header, body


def _parse_public_key_packet_sq(body):
    """
    Return the key described by the body of a single Public-Key Packet

    :param body: Lines of the packet without its header
    :type body: list(str)
    :return: The key described by the packet
    :rtype: GpgKeyInfo
    :raises GpgParseError: The packet lacks a required field or has an unexpected version.
    """
    fields = {}
    for line in body:
        name, _, value = line.strip().partition(':')
        if name in ('Version', 'Fingerprint'):
            fields[name] = value.strip()

    missing = {'Version', 'Fingerprint'} - set(fields)
    if missing:
        error = f'Missing fields {sorted(missing)}'
        raise GpgParseError(error)

    version = fields['Version']
    if version not in _SHORT_KEY_ID_SLICE:
        error = f'Unexpected key version \'{version}\''
        raise GpgParseError(error)

    fingerprint = fields['Fingerprint'].lower()
    return GpgKeyInfo(
        fingerprint=fingerprint,
        short_keyid=fingerprint[_SHORT_KEY_ID_SLICE[version]],
        is_pqc=version == '6',
    )


def _parse_gpg_key_sq(stdin):
    """
    Return the list of public keys read from the given stdin using 'sq'

    Public-Key Packets that cannot be parsed are logged and skipped, the
    remaining keys are still returned.

    :param stdin: Open file descriptor of a file with GPG key(s), or their ascii armor
    :type stdin: int or str
    :return: List of the public keys read from the given stdin
    :rtype: List[GpgKeyInfo]
    :raises GpgReadError: When sq cannot be executed or exits with an error
    """
    try:
        # cli version must be first arg
        cmd = ['sq', '--cli-version', '1.4.0', 'packet', 'dump']
        output = run(cmd, split=True, stdin=stdin)
    except (OSError, CalledProcessError) as err:
        error = f'Failed to read fingerprint from GPG key: {str(err)}'
        raise GpgReadError(error) from err

    gpg_infos = []
    for header, body in _iter_sq_packets(output['stdout']):
        if header.startswith('Public-Key Packet'):
            try:
                gpg_infos.append(_parse_public_key_packet_sq(body))
            except GpgParseError as err:
                # just log the exception, same as _parse_fp_from_gpg() does
                error = f'Failed to parse fingerprint from Public-Key packet {body}: {str(err)}'
                api.current_logger().error(error)

    if not gpg_infos:
        api.current_logger().warning(
            'Unable to parse OpenPGP keys: {}'.format(output.get('stderr', ''))
        )
    return gpg_infos


def _parse_gpg_key(stdin):
    # The sequoia-sq package providing the sq command is available only since RHEL 9.9
    if matches_source_version('< 9.9'):
        return _parse_gpg_key_gpg2(stdin)

    return _parse_gpg_key_sq(stdin)


def parse_gpg_key_from_ascii(ascii_armors):
    """
    Return the list of public keys parsed from the given ascii armor(s)

    The `ascii_armors` string can contain multiple armors (keys). The returned
    list contains a `GpgKeyInfo` for every successfully parsed keys. Failures
    during parsing are logged at the error level and ignored.

    Note that for source systems older than 9.9, where 'sq' is not available,
    the keys are read by gpg2 and so all of them are reported as v4 keys (non pqc).

    :param ascii_armor: Ascii armor with GPG key(s)
    :type ascii_armor: str
    :return: List of the public keys from the given ascii armor
    :rtype: List[GpgKeyInfo]

    :raises GpgReadError: when failed to read the keys using the underlying tool (gpg2 or sq)
    :raise ValueError: when `None` is passed as `ascii_armor`
    """
    if ascii_armors is None:
        # run() does not redirect the stdin of the child when it is None, so gpg2/sq
        # would read the stdin inherited from leapp
        raise ValueError('Expected a string but got None')

    return _parse_gpg_key(ascii_armors)


def parse_gpg_key_from_file(key_path):
    """
    Return the list of public keys parsed from the given file

    The file at `key_path` can contain multiple armors (keys). The returned
    list contains a `GpgKeyInfo` for every successfully parsed keys. Failures
    during parsing are logged at the error level and ignored.

    Note that for source systems older than 9.9, where 'sq' is not available,
    the keys are read by gpg2 and so all of them are reported as v4 keys (non pqc).

    :param key_path: Path to the file with GPG key(s)
    :type key_path: str
    :return: List of the public keys from the given file
    :rtype: list(GpgKeyInfo)

    :raises GpgReadError: When the file cannot be opened, or when failed to read the
        keys using the underlying tool (gpg2 or sq)
    """
    try:
        key_file = open(key_path, 'rb')
    except OSError as err:
        raise GpgReadError(
            f'Failed to open GPG key file {key_path}: {str(err)}'
        ) from err

    with key_file as fp:
        return _parse_gpg_key(fp.fileno())


@deprecated(since='2026-11-09', message='Replaced by parse_gpg_key_from_file()')
def get_gpg_fp_from_file(key_path):
    """
    Return the list of public key fingerprints from the given file

    Log warning in case no OpenPGP data found in the given file or it is not
    readable for some reason.

    Note: This function uses `gpg2` if source system version is < 9.9,
    otherwise `sq` is used.

    :param key_path: Path to the file with GPG key(s)
    :type key_path: str
    :return: List of public key fingerprints from the given file
    :rtype: list(str)
    """
    try:
        fps = parse_gpg_key_from_file(key_path)
    except GpgReadError as err:
        # this could now be propagated, but we need to preserve the api
        api.current_logger().error(err)
        return []

    return [fp.short_keyid for fp in fps]


# TODO when a need for the same function for source arises, or when there is
# reason to deprecate this (re)name this to include "target"
def get_path_to_gpg_certs():
    """
    Get path to the directory with trusted target gpg keys in the common leapp repository.

    GPG keys stored under this directory are considered as trusted and are
    installed during the upgrade process.

    :return: Path to the directory with GPG keys stored under the common leapp repository.
    :rtype: str
    """
    target_major_version = get_target_major_version()
    target_product_type = config.get_product_type('target')
    certs_dir = target_major_version
    # only beta is special in regards to the GPG signing keys
    if target_product_type == 'beta':
        certs_dir = '{}beta'.format(target_major_version)
    distro = config.get_target_distro_id()
    return os.path.join(
        api.get_common_folder_path('distro'),
        distro,
        GPG_CERTS_FOLDER,
        certs_dir
    )


def iter_gpg_keyfiles(root_dir=None, *, include_pqc):
    """
    Yield paths to all the keyfiles in the given directory with trusted gpg keys

    The root directory is expected to contain v4 (traditional) keys only and its
    'pqc' subdirectory v6 (PQC) keys only. This is checked by the
    trusted_gpg_key_dir_check actor. The 'pqc' subdirectory is optional; it is
    present for the target systems with PQC support only.

    :param root_dir: Path to the directory with trusted gpg keys
    :type root_dir: str
    :param include_pqc: Yield also the keyfiles in the 'pqc' subdirectory
    :type include_pqc: bool
    """
    if root_dir is None:
        root_dir = get_path_to_gpg_certs()

    for keyfile in os.listdir(root_dir):
        abs_path = os.path.join(root_dir, keyfile)
        if os.path.isfile(abs_path):
            yield abs_path

    if not include_pqc:
        return

    pqc_path = os.path.join(root_dir, GPG_PQC_CERTS_SUBFOLDER)
    if not os.path.isdir(pqc_path):
        # target systems without PQC support do not have the subdirectory
        return

    for keyfile in os.listdir(pqc_path):
        abs_path = os.path.join(pqc_path, keyfile)
        if os.path.isfile(abs_path):
            yield abs_path


def is_nogpgcheck_set():
    """
    Return True if the GPG check should be skipped.

    The GPG check is skipped if leapp is executed with LEAPP_NOGPGCHECK=1
    or with the --nogpgcheck CLI option. In both cases, actors will see
    LEAPP_NOGPGCHECK is '1'.

    :rtype: bool
    """
    return config.get_env('LEAPP_NOGPGCHECK', False) == '1'
