from leapp.libraries.common.config import get_product_type
from leapp.libraries.stdlib import api
from leapp.models import RepositoriesBlacklisted, RepositoriesFacts, RepositoriesMap


def _is_optional_repo(repo):
    sys_type = get_product_type('source')
    suffix = 'optional-rpms'
    if sys_type != 'ga':
        suffix = 'optional-{}-rpms'.format(sys_type)
    return repo.from_repoid.endswith(suffix)


def _get_list_of_optional_repos():
    """
    Return a dict of optional repositories based on RepositoriesMap: { 'from_repoid' : 'to_repoid'}

    It consumes RepositoriesMap messages and create map (dict) of optional repositories
    on RHEL 7 system to CRB repositories on RHEL 8. See the RepositoriesMap model..
    """
    opt_repo = {}
    repo_map = next(api.consume(RepositoriesMap), None)
    if repo_map:
        for repo in repo_map.repositories:
            if _is_optional_repo(repo):
                opt_repo[repo.from_repoid] = repo.to_repoid
    return opt_repo


def _get_disabled_optional_repo():
    """
    Return a list of disabled optional repositories available on the system.
    """
    opt_repos = _get_list_of_optional_repos()
    repos_blacklist = []
    repo_map = next(api.consume(RepositoriesFacts), None)
    for repo_file in repo_map.repositories:
        for repo in repo_file.data:
            if repo.repoid in opt_repos and not repo.enabled:
                repos_blacklist.append(opt_repos[repo.repoid])
    return repos_blacklist


def process():
    # blacklist CRB repo if optional repo is not enabled
    reposid_blacklist = _get_disabled_optional_repo()
    if reposid_blacklist:
        api.current_logger().info("The optional repository is not enabled. Blacklisting the CRB repository.")
        api.produce(RepositoriesBlacklisted(repoids=reposid_blacklist))
