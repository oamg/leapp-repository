import os

from leapp.libraries.common import config
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api, run
from leapp.models import GpgKey

GPG_CERTS_FOLDER = 'rpm-gpg'


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

    Return list of 8 characters fingerprints per each gpgkey for the given
    output from stdlib.run() or None if some error occurred. Either the
    command return non-zero exit code, the file does not exists, its not
    readable or does not contain any openpgp data.
    """
    if not output or output['exit_code']:
        return []

    # we are interested in the lines of the output starting with "pub:"
    # the colons are used for separating the fields in output like this
    # pub:-:4096:1:999F7CBF38AB71F4:1612983048:::-:::escESC::::::23::0:
    #              ^--------------^ this is the fingerprint we need
    #                      ^------^ but RPM version is just the last 8 chars lowercase
    # Also multiple gpg keys can be stored in the file, so go through all "pub"
    # lines
    gpg_fps = []
    for line in output['stdout']:
        if not line or not line.startswith('pub:'):
            continue
        parts = line.split(':')
        if len(parts) >= 4 and len(parts[4]) == 16:
            gpg_fps.append(parts[4][8:].lower())
        else:
            api.current_logger().warning(
                'Cannot parse the gpg2 output. Line: "{}"'
                .format(line)
            )

    return gpg_fps


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
    res = _gpg_show_keys(key_path)
    fp = _parse_fp_from_gpg(res)
    if not fp:
        error_msg = 'Unable to read OpenPGP keys from {}: {}'.format(key_path, res['stderr'])
        api.current_logger().warning(error_msg)
    return fp


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
    distro = config.get_distro_id()
    return os.path.join(
        api.get_common_folder_path('distro'),
        distro,
        GPG_CERTS_FOLDER,
        certs_dir
    )


def is_nogpgcheck_set():
    """
    Return True if the GPG check should be skipped.

    The GPG check is skipped if leapp is executed with LEAPP_NOGPGCHECK=1
    or with the --nogpgcheck CLI option. In both cases, actors will see
    LEAPP_NOGPGCHECK is '1'.

    :rtype: bool
    """
    return config.get_env('LEAPP_NOGPGCHECK', False) == '1'
