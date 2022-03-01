
from leapp.libraries.actor import setuptargetrepos_repomap
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoriesSetupTasks,
    RHELTargetRepository,
    RHUIInfo,
    SkippedRepositories,
    TargetRepositories,
    UsedRepositories
)


def _get_enabled_repoids():
    """
    Collects repoids of all enabled repositories on the source system.

    :param repositories_facts: Iterable of RepositoriesFacts containing info about repositories on the source system.
    :returns: Set of all enabled repository IDs present on the source system.
    :rtype: Set[str]
    """
    enabled_repoids = set()
    for repos in api.consume(RepositoriesFacts):
        for repo_file in repos.repositories:
            for repo in repo_file.data:
                if repo.enabled:
                    enabled_repoids.add(repo.repoid)
    return enabled_repoids


def _get_blacklisted_repoids():
    repos_blacklisted = set()
    for blacklist in api.consume(RepositoriesBlacklisted):
        repos_blacklisted.update(blacklist.repoids)
    return repos_blacklisted


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


def _setup_repomap_handler(src_repoids):
    repo_mappig_msg = next(api.consume(RepositoriesMapping), RepositoriesMapping())
    rhui_info = next(api.consume(RHUIInfo), RHUIInfo(provider=''))
    repomap = setuptargetrepos_repomap.RepoMapDataHandler(repo_mappig_msg, cloud_provider=rhui_info.provider)
    # TODO(pstodulk): what about skip this completely and keep the default 'ga'..?
    default_channels = setuptargetrepos_repomap.get_default_repository_channels(repomap, src_repoids)
    repomap.set_default_channels(default_channels)
    return repomap


def _get_mapped_repoids(repomap, src_repoids):
    mapped_repoids = set()
    src_maj_ver = get_source_major_version()
    for repoid in src_repoids:
        if repomap.get_pesid_repo_entry(repoid, src_maj_ver):
            mapped_repoids.add(repoid)
    return mapped_repoids


def process():
    # load all data / messages
    used_repoids_dict = _get_used_repo_dict()
    enabled_repoids = _get_enabled_repoids()
    excluded_repoids = _get_blacklisted_repoids()
    custom_repos = _get_custom_target_repos()

    # TODO(pstodulk): isn't that a potential issue that we map just enabled repos
    # instead of enabled + used repos??
    # initialise basic data
    repomap = _setup_repomap_handler(enabled_repoids)
    mapped_repoids = _get_mapped_repoids(repomap, enabled_repoids)
    skipped_repoids = enabled_repoids & set(used_repoids_dict.keys()) - mapped_repoids

    # Now get the info what should be the target RHEL repositories
    expected_repos = repomap.get_expected_target_pesid_repos(enabled_repoids)
    target_rhel_repoids = set()
    for target_pesid, target_pesidrepo in expected_repos.items():
        if not target_pesidrepo:
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
        target_rhel_repoids.add(target_pesidrepo.repoid)

    # FIXME: this could possibly result into a try to enable multiple repositories
    # from the same family (pesid). But unless we have a bug in previous actors,
    # it should not happen :) it's not blocker error anyway, so survive it.
    # - We expect to deliver the fix as part of the refactoring when we merge
    # setuptargetrepos & peseventsscanner actors together (+ blacklistrepos?)
    for task in api.consume(RepositoriesSetupTasks):
        for repo in task.to_enable:
            if repo in excluded_repoids:
                api.current_logger().debug('Skipping the {} repo from setup task (excluded).'.format(repo))
                continue
            target_rhel_repoids.add(repo)

    # create the final lists and sort them (for easier testing)
    rhel_repos = [RHELTargetRepository(repoid=repoid) for repoid in sorted(target_rhel_repoids)]
    custom_repos = [repo for repo in custom_repos if repo.repoid not in excluded_repoids]
    custom_repos = sorted(custom_repos, key=lambda x: x.repoid)

    if skipped_repoids:
        pkgs = set()
        for repo in skipped_repoids:
            pkgs.update(used_repoids_dict[repo])
        api.produce(SkippedRepositories(repos=sorted(skipped_repoids), packages=sorted(pkgs)))

    api.produce(TargetRepositories(
        rhel_repos=rhel_repos,
        custom_repos=custom_repos,
    ))
