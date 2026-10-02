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
from leapp.exceptions import StopActorExecution
from leapp.libraries.actor import tus_constants, tus_rhui
from leapp.libraries.common import distro, repofileutils
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id, is_conversion
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api
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


def _inhibit(title, summary, severity, remediation=None):
    """Create an inhibitor report and soft-stop the actor (no output messages)."""
    report_parts = [
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Severity(severity),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ]
    if remediation:
        report_parts.append(reporting.Remediation(hint=remediation))
    reporting.create_report(report_parts)
    raise StopActorExecution()


def select_target_repositories(context, inputs):
    """
    Discover and select the usable target repositories (§7, §4 step 4).

    :return: :class:`UsedTargetRepositories` with the selected repoids.
    :raises StopActorExecution: on any of inhibitors #2-#5.
    """
    target_repositories = inputs.target_repositories

    distro_repoids = set(distro.get_target_distro_repoids(context))
    rhui_repoids = tus_rhui.discover_client_exposed_repoids(context, inputs.rhui_info)
    discovered = distro_repoids | rhui_repoids
    available = _all_available_repoids(context)

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
    if inputs.skip_rhsm:
        duplicates = repofileutils.get_duplicate_repositories(
            repofileutils.get_parsed_repofiles(context))
        if duplicates:
            details = '\n'.join(
                '{}: {}'.format(repoid, ', '.join(sorted(files)))
                for repoid, files in sorted(duplicates.items())
            )
            _inhibit(
                tus_constants.REPORT_TITLE_DUPLICATE_REPOS,
                'The following repositories are defined in multiple repository'
                ' files, which is not supported:\n{}'.format(details),
                reporting.Severity.MEDIUM,
                remediation='Remove the duplicate repository definitions.',
            )

    # Inhibitor #3 - missing base repositories (baseos/appstream).
    if _base_repo_check_applies(inputs.skip_rhsm) and not _has_base_repos(discovered):
        _inhibit(
            tus_constants.REPORT_TITLE_MISSING_BASE_REPOS,
            'Cannot find the required basic target repositories (BaseOS and'
            ' AppStream). These are needed to build the target userspace.',
            reporting.Severity.HIGH,
            remediation='Ensure the target BaseOS and AppStream repositories are'
                        ' available and enabled for the upgrade.',
        )

    # Inhibitor #4 - no enabled target repositories.
    if not (selected_distro | selected_custom):
        _inhibit(
            tus_constants.REPORT_TITLE_NO_TARGET_REPOS,
            'No enabled target repositories were found among the requested ones.'
            ' At least one usable target repository is required.',
            reporting.Severity.HIGH,
            remediation='Check the requested target repositories and make sure'
                        ' they are available for the upgrade.',
        )

    # Inhibitor #5 - missing custom target repositories.
    missing_custom = requested_custom - available
    if missing_custom:
        _inhibit(
            tus_constants.REPORT_TITLE_MISSING_CUSTOM_REPOS,
            'The following requested custom target repositories are not'
            ' available: {}'.format(', '.join(sorted(missing_custom))),
            reporting.Severity.HIGH,
            remediation='Make the listed custom repositories available or remove'
                        ' them from the requested target repositories.',
        )

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
    """
    repofiles = repofileutils.get_parsed_repofiles(context)
    return RepositoriesFactsTarget(repositories=repofiles)
