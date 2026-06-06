from leapp.libraries.actor import repomap_calc
from leapp.libraries.actor.pes_events_scanner import get_enabled_repoids
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_source_major_version, get_source_version
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    DistroTargetRepository,
    InstalledRPM,
    RHELTargetRepository,
    SkippedRepositories,
    TargetRepositories,
    UsedRepositories
)
from leapp.utils.deprecation import suppress_deprecation

RHUI_CLIENT_REPOIDS_RHEL88_TO_RHEL810 = {
    'rhui-microsoft-azure-rhel8-sapapps': 'rhui-microsoft-azure-rhel8-base-sap-apps',
    'rhui-microsoft-azure-rhel8-sap-ha': 'rhui-microsoft-azure-rhel8-base-sap-ha',
}


def _get_repoids_from_installed_packages():
    repoids_from_installed_packages = set()
    for installed_packages in api.consume(InstalledRPM):
        for rpm_package in installed_packages.items:
            repoids_from_installed_packages.add(rpm_package.repository)
    return repoids_from_installed_packages


def _get_custom_target_repos():
    custom_repos = []
    for repo in api.consume(CustomTargetRepository):
        custom_repos.append(repo)
    return custom_repos


def _get_used_repo_dict():
    """
    Return dict: {used_repoid: [installed_packages]}
    """
    used = {}
    for used_repos in api.consume(UsedRepositories):
        for used_repo in used_repos.repositories:
            used[used_repo.repository] = used_repo.packages
    return used


def _get_mapped_repoids(repomap, src_repoids):
    mapped_repoids = set()
    src_maj_ver = get_source_major_version()
    src_distro = get_source_distro_id()
    for repoid in src_repoids:
        if repomap.get_pesid_repo_entry(repoid, src_maj_ver, src_distro):
            mapped_repoids.add(repoid)
    return mapped_repoids


@suppress_deprecation(RHELTargetRepository)
def setup_target_repos(repomap_handler, pes_requested_repoids=None,
                       blacklisted_repoids=None, external_repoids_requests=None):
    """
    Determine the final list of target repositories.

    :param repomap_handler: Operator to work with the repositories mapping data
    :type repomap_handler: repomap_calc.RepoMapDataHandler
    :param pes_requested_repoids: Set of repoids derived from PES events that need to be enabled.
    :param blacklisted_repoids: Set of repoids to exclude from target repos. If None, an empty set is used.
    :param external_repoids_requests: Set of repoids requested by external actors (e.g. satellite_upgrade_facts).
    """
    # Load relevant data from messages
    used_repoids_dict = _get_used_repo_dict()
    enabled_repoids = get_enabled_repoids()
    excluded_repoids = blacklisted_repoids if blacklisted_repoids is not None else set()
    custom_repos = _get_custom_target_repos()
    repoids_from_installed_packages = _get_repoids_from_installed_packages()

    # Filter set of repoids from installed packages so that it contains only repoids with mapping
    repoids_from_installed_packages_with_mapping = _get_mapped_repoids(
        repomap_handler, repoids_from_installed_packages
    )

    # Set of repoid that are going to be mapped to target repoids containing enabled repoids and also repoids from
    # installed packages that have mapping to prevent missing repositories that are disabled during the upgrade, but
    # can be used to upgrade installed packages.
    repoids_to_map = enabled_repoids.union(repoids_from_installed_packages_with_mapping)

    # RHEL8.10 use a different repoid for client repository, but the repomapping mechanism cannot distinguish these
    # as it does not use minor versions. Therefore, we have to hardcode these changes.
    if get_source_distro_id() == 'rhel' and get_source_version() == '8.10':
        for rhel88_rhui_client_repoid, rhel810_rhui_client_repoid in RHUI_CLIENT_REPOIDS_RHEL88_TO_RHEL810.items():
            if rhel810_rhui_client_repoid in repoids_to_map:
                # Replace RHEL8.10 rhui client repoids with RHEL8.8 repoids,
                # so that they are mapped to target repoids correctly.
                repoids_to_map.remove(rhel810_rhui_client_repoid)
                repoids_to_map.add(rhel88_rhui_client_repoid)

    # Set default repository channels for the repositories mapping
    # TODO(pstodulk): what about skip this completely and keep the default 'ga'..?
    default_channels = repomap_calc.get_default_repository_channels(repomap_handler, repoids_to_map)
    repomap_handler.set_default_channels(default_channels)

    # Get target distro repoids based on the repositories mapping
    expected_repos = repomap_handler.get_expected_target_pesid_repos(repoids_to_map)
    target_distro_repoids = set()
    for target_pesid, target_pesidrepo in expected_repos.items():
        if not target_pesidrepo:
            # NOTE this could happen only for enabled repositories part of the set,
            # since the repositories collected from installed packages already contain
            # only mappable repoids.

            # With the original repomap data, this should not happen (this should
            # currently point to a problem in our data
            # TODO(pstodulk): add report? inhibitor? what should be in the report?
            api.current_logger().error(
                'Missing target repository from the {} family (PES ID).'
                .format(target_pesid)
            )
            continue
        if target_pesidrepo.repoid in excluded_repoids:
            api.current_logger().debug('Skipping the {} repo (excluded).'.format(target_pesidrepo.repoid))
            continue
        target_distro_repoids.add(target_pesidrepo.repoid)

    # FIXME: this could possibly result in enabling multiple repositories
    # from the same family (pesid). Proper fix requires deduplication by
    # PESID family, picking the best candidate per family.
    all_requested_repoids = set(pes_requested_repoids or set())
    all_requested_repoids.update(external_repoids_requests or set())

    for repo in all_requested_repoids:
        if repo in excluded_repoids:
            api.current_logger().debug('Skipping the {} repo from setup task (excluded).'.format(repo))
            continue
        target_distro_repoids.add(repo)

    # create the final lists and sort them (for easier testing)
    if get_target_distro_id() == 'rhel':
        rhel_repos = [RHELTargetRepository(repoid=repoid) for repoid in sorted(target_distro_repoids)]
    else:
        rhel_repos = []
    distro_repos = [DistroTargetRepository(repoid=repoid) for repoid in sorted(target_distro_repoids)]
    custom_repos = [repo for repo in custom_repos if repo.repoid not in excluded_repoids]
    custom_repos = sorted(custom_repos, key=lambda x: x.repoid)

    # produce message about skipped repositories
    enabled_repoids_with_mapping = _get_mapped_repoids(repomap_handler, enabled_repoids)
    skipped_repoids = enabled_repoids & set(used_repoids_dict.keys()) - enabled_repoids_with_mapping
    if skipped_repoids:
        pkgs = set()
        for repo in skipped_repoids:
            pkgs.update(used_repoids_dict[repo])
        api.produce(SkippedRepositories(repos=sorted(skipped_repoids), packages=sorted(pkgs)))

    api.produce(TargetRepositories(
        rhel_repos=rhel_repos,
        distro_repos=distro_repos,
        custom_repos=custom_repos,
    ))
