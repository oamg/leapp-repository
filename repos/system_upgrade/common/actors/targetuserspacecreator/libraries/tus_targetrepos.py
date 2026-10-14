"""
Target repository discovery, selection, and the build-container repo snapshot.

This module provides two entry points:
  * :func:`select_target_repositories` - discovers the repositories available in
    the target userspace container, intersects them with the requested distro,
    RHUI and custom repositories, and reports inhibitors when required
    repositories are missing, duplicated, or none are usable;
  * :func:`build_target_repositories_snapshot` - parses the build (scratch)
    container's repofiles into the produced snapshot message.

This module may import ``tus_rhui``; the reverse direction is not allowed.
"""

from leapp import reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import tus_rhui
from leapp.libraries.common import distro, repofileutils
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id, is_conversion
from leapp.libraries.common.config.version import (
    get_major_version,
    get_source_major_version,
    get_target_major_version,
    get_target_version
)
from leapp.libraries.stdlib import api, format_list
from leapp.models import RepositoriesFactsTarget, RHELTargetRepository, UsedTargetRepositories, UsedTargetRepository
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(RHELTargetRepository)
def _requested_distro_repoids(target_repositories):
    """
    Collect the requested distribution repoids.

    Returns the union of the repoids from ``distro_repos`` and from the
    deprecated ``rhel_repos`` field, which is still honored for backwards
    compatibility.

    :param target_repositories: Target repositories requested for the upgrade.
    :type target_repositories: TargetRepositories
    :returns: Set of requested distribution repoids.
    :rtype: Set[str]
    """
    distro_repos = target_repositories.distro_repos or []
    rhel_repos = target_repositories.rhel_repos or []
    return {repo.repoid for repo in distro_repos} | {repo.repoid for repo in rhel_repos}


def _requested_custom_repoids(target_repositories):
    """
    Collect the requested custom repoids.

    :param target_repositories: Target repositories requested for the upgrade.
    :type target_repositories: TargetRepositories
    :returns: Set of requested custom repoids.
    :rtype: Set[str]
    """
    custom_repos = target_repositories.custom_repos or []
    return {repo.repoid for repo in custom_repos}


def _all_available_repos(context_scratch):
    """
    Collect every repoid defined in the container's repofiles.

    :param context_scratch: Mounting context of the target userspace container.
    :type context_scratch: mounting.IsolatedActions
    :returns: A tuple of all unique repoids found across the container's
              repofiles and a list of the repofiles
    :rtype: Tuple[Set[str], List[RepositoryFile]]
    :raises: StopActorExecutionError when failed to parse the repofiles
    """
    repoids = set()
    try:
        repofiles = repofileutils.get_parsed_repofiles(context_scratch)
    except repofileutils.InvalidRepoDefinition as e:
        raise StopActorExecutionError(
            message=f'Failed to parse available repoids: {str(e)}',
            details={
                'hint': 'Ensure the repository definition is correct or remove it '
                        'if the repository is not required for the upgrade.'
            })
    for repofile in repofiles:
        for repo in repofile.data:
            repoids.add(repo.repoid)
    return repoids, repofiles


def _has_base_repos(repoids):
    """
    Check whether both a baseos and an appstream repository are present.

    The match is case-insensitive and succeeds when a repoid contains the
    substring ``baseos`` and another contains the substring ``appstream``.

    :param repoids: Repoids to inspect.
    :type repoids: Iterable[str]
    :returns: ``True`` if both a baseos and an appstream repoid are present.
    :rtype: bool
    """
    lowered = [repoid.lower() for repoid in repoids]
    has_baseos = any('baseos' in repoid for repoid in lowered)
    has_appstream = any('appstream' in repoid for repoid in lowered)
    return has_baseos and has_appstream


def _base_repo_check_applies(skip_rhsm):
    """
    Decide whether the baseos/appstream presence check should run.

    The check runs by default but is skipped in these cases:
    (a) the upgrade is a conversion;
    (b) the source system is CentOS Stream 8;
    (c) the target system is RHEL and RHSM is being skipped.

    :param skip_rhsm: Whether subscription-manager (RHSM) is being skipped.
    :type skip_rhsm: bool
    :returns: ``True`` if the baseos/appstream presence check applies.
    :rtype: bool
    """
    if is_conversion():
        return False
    source_is_cs8 = get_source_distro_id() == 'centos' and get_source_major_version() == '8'
    if source_is_cs8:
        return False
    target_is_rhel = get_target_distro_id() == 'rhel'
    if target_is_rhel and skip_rhsm:
        return False
    return True


def _inhibit_no_base_repos(target_major_ver):
    """
    Report an inhibitor when the required basic target OS repositories are missing.

    Creates a high-severity inhibitor report stating that the baseos and
    appstream repositories could not be found. For a RHEL target, a remediation
    hint about subscription-manager and a valid SKU is included.

    :param target_major_ver: Major version of the target system.
    :type target_major_ver: str
    """
    report = [
        reporting.Title('Cannot find required basic target OS repositories.'),
        reporting.Summary(
            'This can happen when a repository ID was entered incorrectly either while using the --enablerepo'
            ' option of leapp or in a third party actor that produces a CustomTargetRepositoryMessage.'
        ),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.ExternalLink(
            url='https://access.redhat.com/solutions/5392811',
            title='RHEL 7 to RHEL 8 LEAPP Upgrade Failing When Using Red Hat Satellite'
        ),
        reporting.ExternalLink(
            # https://red.ht/preparing-for-upgrade-to-rhel8
            # https://red.ht/preparing-for-upgrade-to-rhel9
            # https://red.ht/preparing-for-upgrade-to-rhel10
            url=f'https://red.ht/preparing-for-upgrade-to-rhel{target_major_ver}',
            title='Preparing for the upgrade'
        ),
        reporting.Key('f5770a56e540f27d370da7b697cb4a2e81e2c30d'),
    ]
    if get_target_distro_id() == 'rhel':
        report.append(
            reporting.Remediation(hint=(
                'It is required to have RHEL repositories on the system'
                ' provided by the subscription-manager unless the --no-rhsm'
                ' option is specified. You might be missing a valid SKU for'
                ' the target system or have a failed network connection.'
                ' Check whether your system is attached to a valid SKU that is'
                f' providing RHEL {target_major_ver} repositories.'
                ' If you are using Red Hat Satellite, read the upgrade documentation'
                ' to set up Satellite and the system properly.'
            ))
        )
    reporting.create_report(report)


def _inhibit_missing_custom_repos(missing_custom_repos):
    """
    Report an inhibitor when requested custom target repositories are missing.

    Creates a high-severity inhibitor report listing the custom repoids that
    could not be found in the target configuration.

    :param missing_custom_repos: Requested custom repoids that were not found.
    :type missing_custom_repos: Iterable[str]
    """
    reporting.create_report([
        reporting.Title('Some required custom target repositories have not been found'),
        reporting.Summary(
            'This can happen when a repository ID was entered incorrectly either'
            ' while using the --enablerepo option of leapp, or in a third party actor that produces a'
            ' CustomTargetRepositoryMessage.\n'
            'The following repositories IDs could not be found in the target configuration:'
            f'{format_list(missing_custom_repos)}'
        ),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.ExternalLink(
            # NOTE: Article covers both RHEL 7 to RHEL 8 and RHEL 8 to RHEL 9
            url='https://access.redhat.com/articles/4977891',
            title='Customizing your Red Hat Enterprise Linux in-place upgrade'
        ),
        reporting.Remediation(hint=(
            'Consider using the custom repository file, which is documented in the official'
            ' upgrade documentation. Check whether a repository ID has been'
            ' entered incorrectly with the --enablerepo option of leapp.'
            ' Check the leapp logs to see the list of all available repositories.'
        ))
    ])


def _inhibit_no_enabled_target_repos(target_ver):
    """
    Report an inhibitor when no target repositories are enabled.

    Creates a high-severity inhibitor report with remediation hints covering
    subscription-manager registration and, for the ``--no-rhsm`` case, the use
    of custom repository files.

    :param target_ver: Full version of the target system.
    :type target_ver: str
    """
    target_major_ver = get_major_version(target_ver)
    reporting.create_report([
        reporting.Title('There are no enabled target repositories'),
        reporting.Summary(
            'This can happen when a system is not correctly registered with the subscription manager'
            ' or, when the leapp --no-rhsm option has been used, no custom repositories have been'
            ' passed on the command line.'
        ),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Remediation(hint=(
            'Ensure the system is correctly registered with the subscription manager and that'
            f' the current subscription is entitled to install the requested target version {target_ver}.'
            ' If you used the --no-rhsm option (or the LEAPP_NO_RHSM=1 environment variable is set),'
            ' ensure the custom repository file is provided with'
            ' properly defined repositories and that the --enablerepo option for leapp is set if the'
            ' repositories are defined in any repofiles under the /etc/yum.repos.d/ directory.'
            ' For more information on custom repository files, see the documentation.'
            ' Finally, verify that the "/etc/leapp/files/repomap.json" file is up-to-date.'
        )),
        reporting.ExternalLink(
            # https://red.ht/preparing-for-upgrade-to-rhel8
            # https://red.ht/preparing-for-upgrade-to-rhel9
            # https://red.ht/preparing-for-upgrade-to-rhel10
            url=f'https://red.ht/preparing-for-upgrade-to-rhel{target_major_ver}',
            title='Preparing for the upgrade'
        ),
        reporting.ExternalLink(
            url='https://access.redhat.com/solutions/7001181',
            title='LEAPP Upgrade Failing from RHEL 7 to RHEL 8 when system is '
                  'registered to custromer portal'
        ),
        reporting.RelatedResource("file", "/etc/leapp/files/repomap.json"),
        reporting.RelatedResource("file", "/etc/yum.repos.d/")
    ])


def _inhibit_duplicate_repos(duplicates):
    """
    Report an inhibitor when repositories are defined multiple times.

    Creates a medium-severity inhibitor report listing the repoids defined more
    than once inside the upgrade container, with a hint to remove or rename the
    conflicting definitions.

    :param duplicates: Repoids defined more than once.
    :type duplicates: Iterable[str]
    """
    reporting.create_report([
        reporting.Title('A YUM/DNF repository defined multiple times'),
        reporting.Summary(
            'The following repositories are defined multiple times inside the'
            f' "upgrade" container:{format_list(duplicates)}'
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Remediation(hint=(
            'Remove the duplicate repository definitions or change repoids of'
            ' conflicting repositories on the system to prevent the'
            ' conflict.'
            )
        )
    ])


def _discover_distro_and_rhui_target_repositories(context_scratch, rhui_info, target_version):
    """
    Discover the distribution and RHUI repoids available in the container.

    Queries the repoids considered to be provided by the target distribution and,
    when RHUI information is available, the repoids exposed by the RHUI client.
    Both sets are logged and returned.

    :param context_scratch: An entered nspawn scratch container.
    :type context_scratch: mounting.IsolatedActions
    :param rhui_info: RHUI setup information, or a falsy value when not on RHUI.
    :type rhui_info: RHUIInfo
    :param target_version: Full version of the target system.
    :type target_version: str
    :returns: Tuple of (distribution repoids, RHUI repoids).
    :rtype: Tuple[Set[str], Set[str]]

    .. seealso::
        :func:`tus_rhui.discover_client_exposed_repoids`
        for the ``StopActorExecutionError`` raised when RHUI repoids cannot be
        retrieved.
    """
    # TODO: actually, drop this function - load *_repoids in the caller and
    # fold logs into the called functions instead.
    distro_repoids = set(distro.get_target_distro_repoids(context_scratch))
    api.current_logger().info(
        "The following repoids are considered as provided by the '{}' distribution:{}".format(
            get_target_distro_id(),
            format_list(distro_repoids),
        )
    )
    rhui_repoids = tus_rhui.discover_client_exposed_repoids(context_scratch, rhui_info, target_version)
    if rhui_info:
        api.current_logger().info(
            'The following repoids are considered as provided by RHUI cloud provider for RHEL:{}'
            .format(format_list(rhui_repoids))
        )
    return distro_repoids, rhui_repoids


def select_target_repositories(context_scratch, inputs):
    """
    Discover and select the usable target repositories.

    Discovers the distribution, RHUI and all available repoids in the target
    userspace container, intersects them with the requested distro, RHUI and
    custom repositories, and returns the selected set. Several conditions report
    an inhibitor and stop the upgrade: missing basic (baseos/appstream) target
    repositories, duplicate repository definitions (only checked when RHSM is
    skipped), no enabled target repository at all, or requested custom
    repositories that are not available.

    :param context_scratch: An entered nspawn scratch container.
    :type context_scratch: mounting.IsolatedActions
    :param inputs: Collected inputs holding ``rhui_info``, ``skip_rhsm`` and
        ``target_repositories``.
    :type inputs: tus_inputdata.InputData
    :returns: Selected target repositories.
    :rtype: UsedTargetRepositories
    :raises StopActorExecution: When an inhibitor is reported (missing basic
        target repositories, no enabled target repository, or missing requested
        custom repositories).
    :raises StopActorExecutionError: When parsing the container repofiles fails,
        or when the RHUI client repoids cannot be retrieved.
    """
    distro_repoids, rhui_repoids = _discover_distro_and_rhui_target_repositories(
        context_scratch, inputs.rhui_info, get_target_version()
    )
    if _base_repo_check_applies(inputs.skip_rhsm) and not _has_base_repos(distro_repoids):
        # NOTE(pstodulk): RHUI is specific case - in case of problems, the root cause
        # is different from this inhibitor; either handled already earlier or later
        _inhibit_no_base_repos(get_target_major_version())
        raise StopActorExecution()
    available, all_repofiles = _all_available_repos(context_scratch)

    if inputs.skip_rhsm:
        # only if rhsm is skipped, the duplicate repos are not detected
        # automatically and we need to do it extra
        duplicates = repofileutils.get_duplicate_repositories(all_repofiles).keys()
        if duplicates:
            api.current_logger().warning(
                'The following repoids are defined multiple times:{}'.format(
                    format_list(duplicates)
                )
            )
            _inhibit_duplicate_repos(duplicates)

    target_repositories = inputs.target_repositories
    requested_distro = _requested_distro_repoids(target_repositories)
    requested_custom = _requested_custom_repoids(target_repositories)

    discovered_repoids = distro_repoids | rhui_repoids
    selected_distro = requested_distro & discovered_repoids
    # This TODO is preserved from the code before refactor it's about: requested_distro - discovered_repoids

    # TODO: We shall report that the RHEL repos that we deem necessary for
    # the upgrade are not available; but currently it would just print bunch of
    # data every time as we maps EUS and other repositories as well. But these
    # do not have to be necessary available on the target system in the time
    # of the upgrade. Let's skip it for now until it's clear how we will deal
    # with it.

    selected_custom = requested_custom & available

    # Detect duplicate repositories, ONLY when RHSM is being skipped.
    # TODO might be able to drop duplicates detection from the rhsm lib and
    # then it would be here in a single place

    # No enabled target repositories at all.
    if not selected_distro | selected_custom:
        _inhibit_no_enabled_target_repos(get_target_version())
        raise StopActorExecution()

    # Requested custom target repositories that are missing.
    missing_custom = requested_custom - available
    if missing_custom:
        _inhibit_missing_custom_repos(missing_custom)
        raise StopActorExecution()

    selected = sorted(selected_distro | selected_custom)
    api.current_logger().info('Selected target repositories: {}'.format(format_list(selected)))
    return UsedTargetRepositories(
        repos=[UsedTargetRepository(repoid=repoid) for repoid in selected]
    )


def build_target_repositories_snapshot(context):
    """
    Parse the build (scratch) container's repofiles into a snapshot message.

    The parsed repofiles preserve their ``additional_fields`` (where gpg-key
    data lives), which is later consumed by the ``missinggpgkeysinhibitor``
    actor.

    :param context: Mounting context of the build (scratch) container.
    :type context: mounting.IsolatedActions
    :returns: Snapshot of the container's repositories.
    :rtype: RepositoriesFactsTarget
    :raises StopActorExecutionError: When parsing the container repofiles fails.
    """
    try:
        repofiles = repofileutils.get_parsed_repofiles(context)
    except repofileutils.InvalidRepoDefinition as e:
        raise StopActorExecutionError(
            message=f"Failed to parse target system repofiles: {str(e)}",
            details={
                'hint': 'Ensure the repository definition is correct or remove it '
                    'if the repository is not needed anymore. '
                    'This issue is typically caused by missing definition of the name field. '
                    'For more information, see: https://access.redhat.com/solutions/6969001.'
            })

    return RepositoriesFactsTarget(repositories=repofiles)
