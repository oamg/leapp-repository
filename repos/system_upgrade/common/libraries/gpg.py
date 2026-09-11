from collections import namedtuple
import os

from leapp.libraries.common import config
from leapp.libraries.common.config.version import get_source_version, get_target_major_version, matches_version
from leapp.libraries.stdlib import CalledProcessError, api, run
from leapp.models import GpgKey

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


class GpgParseError(Exception):
    pass


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


def _gpg_show_keys(key_path):
    """
    Show keys in given file in version-agnostic manner

    This runs gpg --show-keys to verify the given file exists, is readable and
    contains valid OpenPGP key data, which is printed in parsable format (--with-colons).
    """
    try:
        cmd = ['gpg2', '--show-keys', '--with-colons', key_path]
        # TODO: discussed, most likely the checked=False will be dropped
        # and error will be handled in other functions
        return run(cmd, split=True, checked=False)
    except OSError as err:
        # NOTE: this is hypothetic; gnupg2 has to be installed on RHEL 7+
        error = 'Failed to read fingerprint from GPG key {}: {}'.format(key_path, str(err))
        api.current_logger().error(error)
        return {}


def _parse_fp_from_gpg(output):
    """
    Parse the output of gpg --show-keys --with-colons.

    TODO
    Return list of 8 characters fingerprints per each gpgkey for the given
    output from stdlib.run() or None if some error occurred. Either the
    command return non-zero exit code, the file does not exists, its not
    readable or does not contain any openpgp data.

    Example input (output of gpg2 --show-keys --with-fingerprint):
    pub:-:4096:1:199E2F91FD431D51:1256212795:::-:::scSC::::::23::0:
    fpr:::::::::567E347AD0044ADE55BA8A5F199E2F91FD431D51:
    uid:-::::1256212796::DC1CAEC7997B3575101BB0FCAAC6191792660D8F::Red Hat, Inc. (release key 2) <security@redhat.com>::::::::::0:

    The full fingerprint is field 10 in the fpr line.

    """
    if not output or output['exit_code']:
        return []

    gpg_fps = []
    for line in output['stdout']:
        if not line or not line.startswith('fpr:'):
            continue
        parts = line.split(':')
        if len(parts) >= 9 and len(parts[9]) == 40:
            gpg_fps.append(parts[9].lower())
        else:
            api.current_logger().warning(
                'Cannot parse the gpg2 output. Line: "{}"'
                .format(line)
            )

    return gpg_fps


GpgKeyInfo = namedtuple('GpgKeyInfo', ('fingerprint', 'short_keyid', 'is_pqc'))


def _parse_gpg_key_gpg2(key_path):
    """
    Return the list of public keys stored in the given file using 'gpg2'

    All the keys are reported as v4 keys. gpg2 cannot read v6 (PQC) keys at
    all, so such keys are skipped with a warning instead of being reported.

    :param key_path: Path to the file with GPG key(s)
    :type key_path: str
    :return: List of the public keys from the given file
    :rtype: list(dict)
    """
    output = _gpg_show_keys(key_path)

    # hardcode is_pqc=False because gpg2 cannot parse v6 keys so no pqc
    keys = [
        GpgKeyInfo(
            fingerprint=fp,
            short_keyid=fp[_SHORT_KEY_ID_SLICE['4']],
            is_pqc=False
        )
        for fp in _parse_fp_from_gpg(output)
    ]

    if not keys:
        api.current_logger().warning(
            'Unable to read OpenPGP keys from {}: {}'.format(key_path, output.get('stderr', ''))
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


def _parse_public_key_packet_sq(body, key_path):
    """
    Return the key described by the body of a single Public-Key Packet

    :param body: Lines of the packet without its header
    :type body: list(str)
    :param key_path: Path to the file the packet comes from (used in error messages only)
    :type key_path: str
    :return: The 'version' of the key and its 'fingerprint' cut to the short key ID
    :rtype: dict
    :raises GpgParseError: The packet lacks a required field or has an unexpected version.
    """
    fields = {}
    for line in body:
        name, _, value = line.strip().partition(':')
        if name in ('Version', 'Fingerprint'):
            fields[name] = value.strip()

    missing = {'Version', 'Fingerprint'} - set(fields)
    if missing:
        error = 'Missing fields {} of a key in the keyfile {}'.format(sorted(missing), key_path)
        raise GpgParseError(error)

    version = fields['Version']
    if version not in _SHORT_KEY_ID_SLICE:
        error = 'Unexpected key version \'{}\' in the keyfile {}'.format(version, key_path)
        raise GpgParseError(error)

    short_keyid = fields['Fingerprint'].lower()[_SHORT_KEY_ID_SLICE[version]]
    return GpgKeyInfo(
        fingerprint=fields['Fingerprint'],
        short_keyid=short_keyid,
        is_pqc=version == '6',
    )


def _parse_gpg_key_sq(key_path):
    """
    Return the list of public keys stored in the given file using 'sq'

    :param key_path: Path to the file with GPG key(s)
    :type key_path: str
    :return: List of the public keys from the given file
    :rtype: list(GpgKeyInfo)
    """
    try:
        cmd = ['sq', 'packet', 'dump', key_path]
        output = run(cmd, split=True)
    except (OSError, CalledProcessError) as err:
        error = 'Failed to read fingerprint from GPG key {}: {}'.format(key_path, str(err))
        api.current_logger().error(error)
        # if can't be read, return empty, same as _parse_fp_from_gpg()
        return []

    gpg_infos = []
    for header, body in _iter_sq_packets(output['stdout']):
        if header.startswith('Public-Key Packet'):
            try:
                gpg_infos.append(_parse_public_key_packet_sq(body, key_path))
            except GpgParseError as err:
                # just log the exception, same as _parse_fp_from_gpg() does
                error = 'Failed to parse GPG key {}: {}'.format(key_path, str(err))
                api.current_logger().error(error)

    return gpg_infos


def parse_gpg_key_from_file(key_path):
    """
    Return the list of public keys stored in the given file

    Every key is described by its 'version' and 'fingerprint' cut to the short
    key ID, i.e. the same value as used in the version of the gpg-pubkey RPMs.

    Note that on source systems older than 9.8, where 'sq' is not available,
    the keys are read by gpg2 and so all of them are reported as v4 keys.

    :param key_path: Path to the file with GPG key(s)
    :type key_path: str
    :return: List of the public keys from the given file
    :rtype: list(GpgKeyInfo)
    """
    # TODO: 9.6 will be dropped from upgrade paths at the point this gets released
    if matches_version(['< 9.8'], get_source_version()):
        return _parse_gpg_key_gpg2(key_path)

    return _parse_gpg_key_sq(key_path)


def get_gpg_fp_from_file(key_path):
    """
    Return the list of public key fingerprints from the given file

    Log warning in case no OpenPGP data found in the given file or it is not
    readable for some reason.

    :param key_path: Path to the file with GPG key(s)
    :type key_path: str
    :return: List of public key fingerprints from the given file
    :rtype: list(str)
    """
    fps = parse_gpg_key_from_file(key_path)
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
