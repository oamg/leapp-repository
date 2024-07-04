import json
import os
import re
import shutil
import tempfile

from six.moves import urllib

from leapp import reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.gpg import get_gpg_fp_from_file, get_path_to_gpg_certs, is_nogpgcheck_set
from leapp.libraries.stdlib import api
from leapp.models import (
    DNFWorkaround,
    TargetUserSpaceInfo,
    TMPTargetRepositoriesFacts,
    TrustedGpgKeys,
    UsedTargetRepositories
)
from leapp.utils.deprecation import suppress_deprecation

FMT_LIST_SEPARATOR = '\n    - '


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


def _consume_data():
    try:
        target_userspace = next(api.consume(TargetUserSpaceInfo))
    except StopIteration:
        api.current_logger().warning(
            'Missing TargetUserSpaceInfo data. The upgrade cannot continue'
            'without this data, so skipping any other actions.'
        )
        raise StopActorExecution()

    try:
        used_target_repos = next(api.consume(UsedTargetRepositories)).repos
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={
                'details': 'No UsedTargetRepositories facts',
                'link': 'https://access.redhat.com/solutions/7061850'
            }
        )

    try:
        target_repos = next(api.consume(TMPTargetRepositoriesFacts)).repositories
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No TMPTargetRepositoriesFacts facts'}
        )
    try:
        trusted_gpg_keys = next(api.consume(TrustedGpgKeys))
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No TrustedGpgKeys facts'}
        )

    return used_target_repos, target_repos, trusted_gpg_keys, target_userspace


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
        .format(get_path_to_gpg_certs())
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
        .format(trust_dir=get_path_to_gpg_certs())
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
        script_args=[get_path_to_gpg_certs()],
    ))


@suppress_deprecation(TMPTargetRepositoriesFacts)
def process():
    """
    Process the repositories and find missing signing keys

    UsedTargetRepositories doesn't contain baseurl attribute. So gathering
    them from model TMPTargetRepositoriesFacts.
    """
    # when the user decided to ignore gpg signatures on the packages, we can ignore these checks altogether
    if is_nogpgcheck_set():
        api.current_logger().warning('The --nogpgcheck option is used: skipping all related checks.')
        return

    used_target_repos, target_repos, trusted_gpg_keys, target_userspace = _consume_data()

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

    pubkeys = [key.fingerprint for key in trusted_gpg_keys.items]
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
            fps = get_gpg_fp_from_file(key_file)
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
