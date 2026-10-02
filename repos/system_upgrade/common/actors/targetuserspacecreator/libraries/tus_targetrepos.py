"""
Target repository discovery, selection, and the build-container repo snapshot
(§7 + inhibitors #2-#5).

Two entry points:
  * :func:`select_target_repositories` - discover + select the usable target
    repos, raising the repo inhibitors (§4 step 4);
  * :func:`build_target_repositories_snapshot` - parse the build (scratch)
    container's repofiles into the produced snapshot message (§4 step 6).

Mid-layer module: may import ``tus_rhui``; never the reverse.
"""

from leapp import reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import tus_rhui
from leapp.libraries.common import distro, repofileutils
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id, is_conversion
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version, get_target_version
from leapp.libraries.stdlib import api, format_list
from leapp.models import RepositoriesFactsTarget, RHELTargetRepository, UsedTargetRepositories, UsedTargetRepository
from leapp.utils.deprecation import suppress_deprecation

# FIXME unhandled exceptions from calls to functions in repofiles lib


@suppress_deprecation(RHELTargetRepository)
def _requested_distro_repoids(target_repositories):
    """
    Requested distro repoids: the union of ``distro_repos`` and the still
    deprecated ``rhel_repos`` (§7; rhel_repos kept per user instruction).
    """
    distro_repos = target_repositories.distro_repos or []
    rhel_repos = target_repositories.rhel_repos or []
    return {repo.repoid for repo in distro_repos} | {repo.repoid for repo in rhel_repos}


def _requested_custom_repoids(target_repositories):
    custom_repos = target_repositories.custom_repos or []
    return {repo.repoid for repo in custom_repos}


def _all_available_repoids(context):
    """All repoids defined in the container's repofiles."""
    repoids = set()
    for repofile in repofileutils.get_parsed_repofiles(context):
        for repo in repofile.data:
            repoids.add(repo.repoid)
    return repoids


def _has_base_repos(repoids):
    """Whether both a baseos and an appstream repo are present in ``repoids``."""
    lowered = [repoid.lower() for repoid in repoids]
    has_baseos = any('baseos' in repoid for repoid in lowered)
    has_appstream = any('appstream' in repoid for repoid in lowered)
    return has_baseos and has_appstream


def _base_repo_check_applies(skip_rhsm):
    """
    The baseos/appstream presence check runs by default and is skipped for:
    (a) conversions; (b) source CentOS Stream 8; (c) RHEL target with RHSM
    skipped (§7).
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


def _inhibit_no_enabled_target_repos(target_major_ver, target_ver):
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


def select_target_repositories(context, inputs):
    """
    Discover and select the usable target repositories (§7, §4 step 4).

    :return: :class:`UsedTargetRepositories` with the selected repoids.
    :raises StopActorExecution: on any of inhibitors #2-#5.
    :raises StopActorExecutionError: on error (e.g. failed parsing repofiles)
    """
    target_major_ver = get_target_major_version()
    target_ver = get_target_version()

    target_repositories = inputs.target_repositories

    distro_repoids = set(distro.get_target_distro_repoids(context))
    # TODO on orig this only works with distro_repoids, but maybe it should count with rhui_repoids too?
    api.current_logger().info(
        "The following repoids are considered as provided by the '{}' distribution:{}".format(
            get_target_distro_id(),
            format_list(distro_repoids),
        )
    )

    rhui_repoids = tus_rhui.discover_client_exposed_repoids(context, inputs.rhui_info)
    discovered = distro_repoids | rhui_repoids
    try:
        available = _all_available_repoids(context)
    except repofileutils.InvalidRepoDefinition as e:
        raise StopActorExecutionError(
            message="Failed to parse available repoids: {}".format(str(e)),
            details={
                'hint': 'Ensure the repository definition is correct or remove it '
                        'if the repository is not required for the upgrade.'
            })

    requested_distro = _requested_distro_repoids(target_repositories)
    requested_custom = _requested_custom_repoids(target_repositories)

    selected_distro = requested_distro & discovered
    # This TODO is preserved from the code before refactor it's about: requested_distro - distro_repoids

    # TODO: We shall report that the RHEL repos that we deem necessary for
    # the upgrade are not available; but currently it would just print bunch of
    # data every time as we maps EUS and other repositories as well. But these
    # do not have to be necessary available on the target system in the time
    # of the upgrade. Let's skip it for now until it's clear how we will deal
    # with it.

    selected_custom = requested_custom & available

    # Inhibitor #2 - duplicate repositories, ONLY when RHSM is being skipped.
    # TODO might be able to drop duplicates detection from the rhsm lib and
    # then it would be here in a single place
    if inputs.skip_rhsm:
        # only if rhsm is skipped, the duplicate repos are not detected
        # automatically and we need to do it extra

        # FIXME handle error
        duplicates = repofileutils.get_duplicate_repositories(
            repofileutils.get_parsed_repofiles(context))
        if duplicates:
            api.current_logger().warning(
                'The following repoids are defined multiple times:{}'.format(
                    format_list(duplicates)
                )
            )
            _inhibit_duplicate_repos(duplicates)

    # Inhibitor #3 - missing base repositories (baseos/appstream).
    # TODO in orig code this works with distro_repoids only, excluding rhui_repoids, that might be a bug in orig?
    # TODO in orig this is done right after getting distro repoids
    if _base_repo_check_applies(inputs.skip_rhsm) and not _has_base_repos(discovered):
        _inhibit_no_base_repos(target_major_ver)
        raise StopActorExecution()

    # Inhibitor #4 - no enabled target repositories.
    if not (selected_distro | selected_custom):
        _inhibit_no_enabled_target_repos(target_major_ver, target_ver)
        raise StopActorExecution()

    # Inhibitor #5 - missing custom target repositories.
    missing_custom = requested_custom - available
    if missing_custom:
        _inhibit_missing_custom_repos(missing_custom)
        raise StopActorExecution()

    selected = sorted(selected_distro | selected_custom)
    api.current_logger().info('Selected target repositories: {}'.format(', '.join(selected)))
    return UsedTargetRepositories(
        repos=[UsedTargetRepository(repoid=repoid) for repoid in selected]
    )


def build_target_repositories_snapshot(context):
    """
    Parse the build (scratch) container's repofiles into the snapshot message (§4 step 6).

    Preserves ``additional_fields`` (where gpg-key data lives, consumed by
    ``missinggpgkeysinhibitor``).

    :raises StopActorExecutionError: If repofile parsing fails
    """
    try:
        repofiles = repofileutils.get_parsed_repofiles(context)
    except repofileutils.InvalidRepoDefinition as e:
        raise StopActorExecutionError(
            message="Failed to parse target system repofiles: {}".format(str(e)),
            details={
                'hint': 'Ensure the repository definition is correct or remove it '
                    'if the repository is not needed anymore. '
                    'This issue is typically caused by missing definition of the name field. '
                    'For more information, see: https://access.redhat.com/solutions/6969001.'
            })

    return RepositoriesFactsTarget(repositories=repofiles)
