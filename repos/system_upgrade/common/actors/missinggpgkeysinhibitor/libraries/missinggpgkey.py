import json
import os
import re
import shutil
import tempfile

from six.moves import urllib

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import config
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.stdlib import api, run
from leapp.models import (
    DNFWorkaround,
    InstalledRPM,
    TargetUserSpaceInfo,
    TMPTargetRepositoriesFacts,
    UsedTargetRepositories
)
from leapp.utils.deprecation import suppress_deprecation

GPG_CERTS_FOLDER = 'rpm-gpg'
FMT_LIST_SEPARATOR = '\n    - '


def _gpg_show_keys(key_path):
    """
    Show keys in given file in version-agnostic manner

    This runs gpg --show-keys (EL8) or gpg --with-fingerprints (EL7)
    to verify the given file exists, is readable and contains valid
    OpenPGP key data, which is printed in parsable format (--with-colons).
    """
    try:
        cmd = ['gpg2']
        # RHEL7 gnupg requires different switches to get the same output
        if get_source_major_version() == '7':
            cmd.append('--with-fingerprint')
        else:
            cmd.append('--show-keys')
        cmd += ['--with-colons', key_path]
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


def _read_gpg_fp_from_file(key_path):
    """
    Returns the list of public key fingerprints from the given file

    Logs warning in case no OpenPGP data found in the given file or it is not
    readable for some reason.
    """
    res = _gpg_show_keys(key_path)
    fp = _parse_fp_from_gpg(res)
    if not fp:
        error = 'Unable to read OpenPGP keys from {}: {}'.format(key_path, res['stderr'])
        api.current_logger().error(error)
    return fp


def _get_path_to_gpg_certs():
    """
    Get path to the directory with trusted target gpg keys in leapp tree
    """
    # XXX This is copy&paste from TargetUserspaceCreator actor.
    # Potential changes need to happen in both places to keep them in sync.
    target_major_version = get_target_major_version()
    target_product_type = config.get_product_type('target')
    certs_dir = target_major_version
    # only beta is special in regards to the GPG signing keys
    if target_product_type == 'beta':
        certs_dir = '{}beta'.format(target_major_version)
    return os.path.join(api.get_common_folder_path(GPG_CERTS_FOLDER), certs_dir)


def _expand_vars(path):
    """
    Expand variables like $releasever and $basearch to the target system version
    """
    r = path.replace('$releasever', get_target_major_version())
    r = r.replace('$basearch', api.current_actor().configuration.architecture)
    return r


def _get_abs_file_path(target_userspace, file_url):
    """
    Return the absolute path for file_url if starts with file:///

    If the file_url starts with 'file:///', return its absolute path to
    the target userspace container, as such a file is supposed to be located
    on the target system. If the path does not exist in the container, the
    the path to the source OS filesystem is returned regardless it exists or not.

    For all other cases, return the originally obtained value.
    """
    if not isinstance(target_userspace, TargetUserSpaceInfo):
        # not need to cover this by tests, it's seatbelt
        raise ValueError('target_userspace must by TargetUserSpaceInfo object')

    prefix = 'file:///'
    if not file_url.startswith(prefix):
        return file_url

    file_path = file_url[len(prefix):]
    expanded = os.path.join(target_userspace.path, file_path)
    if os.path.exists(expanded):
        return expanded

    # the file does not exist in the container -- try the path in the source OS
    return os.path.join('/', file_path)


def _pubkeys_from_rpms(installed_rpms):
    """
    Return the list of fingerprints of GPG keys in RPM DB

    This function returns short 8 characters fingerprints of trusted GPG keys
    "installed" in the source OS RPM database. These look like normal packages
    named "gpg-pubkey" and the fingerprint is present in the version field.
    """
    return [pkg.version for pkg in installed_rpms.items if pkg.name == 'gpg-pubkey']


def _get_pubkeys(installed_rpms):
    """
    Get pubkeys from installed rpms and the trusted directory
    """
    pubkeys = _pubkeys_from_rpms(installed_rpms)
    certs_path = _get_path_to_gpg_certs()
    for certname in os.listdir(certs_path):
        key_file = os.path.join(certs_path, certname)
        fps = _read_gpg_fp_from_file(key_file)
        if fps:
            pubkeys += fps
        # TODO: what about else: ?
        # The warning is now logged in _read_gpg_fp_from_file. We can raise
        # the priority of the message or convert it to report though.
    return pubkeys


def _the_nogpgcheck_option_used():
    return config.get_env('LEAPP_NOGPGCHECK', False) == '1'


def _consume_data():
    try:
        used_target_repos = next(api.consume(UsedTargetRepositories)).repos
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No UsedTargetRepositories facts'}
        )

    try:
        target_repos = next(api.consume(TMPTargetRepositoriesFacts)).repositories
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No TMPTargetRepositoriesFacts facts'}
        )
    try:
        installed_rpms = next(api.consume(InstalledRPM))
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No InstalledRPM facts'}
        )
    try:
        target_userspace = next(api.consume(TargetUserSpaceInfo))
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No TargetUserSpaceInfo facts'}
        )

    return used_target_repos, target_repos, installed_rpms, target_userspace


def _get_repo_gpgkey_urls(repo):
    """
    Return the list or repository gpgkeys that should be checked

    If the gpgcheck is disabled for the repo or gpgkey is not specified,
    return an empty list.

    Returned gpgkeys are URLs with already expanded variables
    (e.g. $releasever) as gpgkey can contain list of URLs separated by comma
    or whitespaces.
    If gpgcheck=0 is present in the repo file, [] is returned. If the
    gpgcheck is missing or enabled and no gpgkey is present, None is
    returned, which means the repo can not be checked.
    """

    if not repo.additional_fields:
        return None

    repo_additional = json.loads(repo.additional_fields)

    # TODO does the case matter here?
    if 'gpgcheck' in repo_additional and repo_additional['gpgcheck'] in ('0', 'False', 'no'):
        # NOTE: https://dnf.readthedocs.io/en/latest/conf_ref.html#boolean-label
        # nothing to do with repos with enforced gpgcheck=0
        return []

    if 'gpgkey' not in repo_additional:
        # This means rpm will bail out at some time if the key is not present
        # but we will not know if the needed key is present or not before we will have
        # the packages at least downloaded
        api.current_logger().warning(
            'The gpgcheck for the {} repository is enabled'
            ' but gpgkey is not specified. Cannot be checked.'
            .format(repo.repoid)
        )
        return None

    return re.findall(r'[^,\s]+', _expand_vars(repo_additional['gpgkey']))


def _report(title, summary, keys, inhibitor=False):
    summary = (
        '{summary}'
        ' Leapp is not able to guarantee validity of such gpg keys and manual'
        ' review is required, so any spurious keys are not imported in the system'
        ' during the in-place upgrade.'
        ' The following additional gpg keys are required to be imported during'
        ' the upgrade:{sep}{key_list}'
        .format(
            summary=summary,
            sep=FMT_LIST_SEPARATOR,
            key_list=FMT_LIST_SEPARATOR.join(keys)
        )
    )
    hint = (
        'Check the path to the listed GPG keys is correct, the keys are valid and'
        ' import them into the host RPM DB or store them inside the {} directory'
        ' prior the upgrade.'
        ' If you want to proceed the in-place upgrade without checking any RPM'
        ' signatures, execute leapp with the `--nogpgcheck` option.'
        .format(_get_path_to_gpg_certs())
    )
    groups = [reporting.Groups.REPOSITORY]
    if inhibitor:
        groups.append(reporting.Groups.INHIBITOR)
    reporting.create_report(
        [
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups(groups),
            reporting.Remediation(hint=hint),
            # TODO(pstodulk): @Jakuje: let's sync about it
            # TODO update external documentation ?
            # reporting.ExternalLink(
            #     title=(
            #         "Customizing your Red Hat Enterprise Linux "
            #         "in-place upgrade"
            #     ),
            #     url=(
            #         "https://access.redhat.com/articles/4977891/"
            #         "#repos-known-issues"
            #     ),
            # ),
        ]
    )


def _report_missing_keys(keys):
    summary = (
        'Some of the target repositories require GPG keys that are not installed'
        ' in the current RPM DB or are not stored in the {trust_dir} directory.'
        .format(trust_dir=_get_path_to_gpg_certs())
    )
    _report('Detected unknown GPG keys for target system repositories', summary, keys, True)


def _report_failed_download(keys):
    summary = (
        'Some of the target repositories require GPG keys that are referenced'
        ' using remote protocol (http:// or https://) but can not be downloaded.'
    )
    _report('Failed to download GPG key for target repository', summary, keys)


def _report_unknown_protocol(keys):
    summary = (
        'Some of the target repositories require GPG keys that are provided'
        ' using unknown protocol.'
    )
    _report('GPG keys provided using unknown protocol', summary, keys)


def _report_invalid_keys(keys):
    summary = (
        'Some of the target repositories require GPG keys, which point to files'
        ' that do not contain any gpg keys.'
    )
    _report('Failed to read GPG keys from provided key files', summary, keys)


def _report_repos_missing_keys(repos):
    summary = (
        'Some of the target repositories require checking GPG signatures, but do'
        ' not provide any gpg keys.'
        ' Leapp is not able to guarantee validity of such gpg keys and manual'
        ' review is required, so any spurious keys are not imported in the system'
        ' during the in-place upgrade.'
        ' The following repositories require some attention before the upgrade:'
        ' {sep}{key_list}'
        .format(
            sep=FMT_LIST_SEPARATOR,
            key_list=FMT_LIST_SEPARATOR.join(repos)
        )
    )
    hint = (
        'Check the repositories are correct and either add a respective gpgkey='
        ' option, disable checking RPM signature using gpgcheck=0 per-repository.'
        ' If you want to proceed the in-place upgrade without checking any RPM'
        ' signatures, execute leapp with the `--nogpgcheck` option.'
    )
    groups = [reporting.Groups.REPOSITORY]
    reporting.create_report(
        [
            reporting.Title('Inconsistent repository without GPG key'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups(groups),
            reporting.Remediation(hint=hint),
            # TODO(pstodulk): @Jakuje: let's sync about it
            # TODO update external documentation ?
            # reporting.ExternalLink(
            #     title=(
            #         "Customizing your Red Hat Enterprise Linux "
            #         "in-place upgrade"
            #     ),
            #     url=(
            #         "https://access.redhat.com/articles/4977891/"
            #         "#repos-known-issues"
            #     ),
            # ),
        ]
    )


def register_dnfworkaround():
    api.produce(DNFWorkaround(
        display_name='import trusted gpg keys to RPM DB',
        script_path=api.current_actor().get_common_tool_path('importrpmgpgkeys'),
        script_args=[_get_path_to_gpg_certs()],
    ))


@suppress_deprecation(TMPTargetRepositoriesFacts)
def process():
    """
    Process the repositories and find missing signing keys

    UsedTargetRepositories doesn't contain baseurl attribute. So gathering
    them from model TMPTargetRepositoriesFacts.
    """
    # when the user decided to ignore gpg signatures on the packages, we can ignore these checks altogether
    if _the_nogpgcheck_option_used():
        api.current_logger().warning('The --nogpgcheck option is used: skipping all related checks.')
        return

    used_target_repos, target_repos, installed_rpms, target_userspace = _consume_data()

    target_repo_id_to_repositories_facts_map = {
        repo.repoid: repo
        for repofile in target_repos
        for repo in repofile.data
    }

    # For reporting all the issues in one batch instead of reporting each issue in separate report
    missing_keys = list()
    failed_download = list()
    unknown_protocol = list()
    invalid_keys = list()
    repos_missing_keys = list()

    # These are used only for getting the installed gpg-pubkey "packages"
    pubkeys = _get_pubkeys(installed_rpms)
    processed_gpgkey_urls = set()
    tmpdir = None
    for repoid in used_target_repos:
        if repoid.repoid not in target_repo_id_to_repositories_facts_map:
            api.current_logger().warning('The target repository {} metadata not available'.format(repoid.repoid))
            continue

        repo = target_repo_id_to_repositories_facts_map[repoid.repoid]
        gpgkeys = _get_repo_gpgkey_urls(repo)
        if gpgkeys is None:
            repos_missing_keys.append(repo.repoid)
            continue
        for gpgkey_url in gpgkeys:
            if gpgkey_url in processed_gpgkey_urls:
                continue
            processed_gpgkey_urls.add(gpgkey_url)

            if gpgkey_url.startswith('file:///'):
                key_file = _get_abs_file_path(target_userspace, gpgkey_url)
            elif gpgkey_url.startswith('http://') or gpgkey_url.startswith('https://'):
                # delay creating temporary directory until we need it
                tmpdir = tempfile.mkdtemp() if tmpdir is None else tmpdir
                # FIXME: what to do with dummy? it's fd, that should be closed also
                dummy, tmp_file = tempfile.mkstemp(dir=tmpdir)
                try:
                    urllib.request.urlretrieve(gpgkey_url, tmp_file)
                    key_file = tmp_file
                except urllib.error.URLError as err:
                    api.current_logger().warning(
                        'Failed to download the gpgkey {}: {}'.format(gpgkey_url, str(err)))
                    failed_download.append(gpgkey_url)
                    continue
            else:
                unknown_protocol.append(gpgkey_url)
                api.current_logger().error(
                    'Skipping unknown protocol for gpgkey {}'.format(gpgkey_url))
                continue
            fps = _read_gpg_fp_from_file(key_file)
            if not fps:
                invalid_keys.append(gpgkey_url)
                api.current_logger().warning(
                    'Cannot get any gpg key from the file: {}'.format(gpgkey_url)
                )
                continue
            for fp in fps:
                if fp not in pubkeys and gpgkey_url not in missing_keys:
                    missing_keys.append(_get_abs_file_path(target_userspace, gpgkey_url))

    if tmpdir:
        # clean up temporary directory with downloaded gpg keys
        shutil.rmtree(tmpdir)

    # report
    if failed_download:
        _report_failed_download(failed_download)
    if unknown_protocol:
        _report_unknown_protocol(unknown_protocol)
    if invalid_keys:
        _report_invalid_keys(invalid_keys)
    if missing_keys:
        _report_missing_keys(missing_keys)
    if repos_missing_keys:
        _report_repos_missing_keys(repos_missing_keys)

    register_dnfworkaround()
