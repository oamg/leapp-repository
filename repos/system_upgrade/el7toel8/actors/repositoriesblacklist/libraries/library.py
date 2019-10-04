from leapp.libraries.stdlib import api
from leapp.models import RepositoriesBlacklisted, RepositoriesFacts, RepositoriesMap


def _get_list_of_optional_repos():
    """
    Return a dict of optional repositories based on RepositoriesMap: { 'from_id' : 'to_id'}

    It consumes RepositoriesMap messages and create map (dict) of optional repositories
    on RHEL 7 system to CRB repositories on RHEL 8. See the RepositoriesMap model..
    """
    opt_repo = {}
    repo_map = next(api.consume(RepositoriesMap), None)
    if repo_map:
        for repo in repo_map:
            if repo.from_id.endswith('optional-rpms'):
                opt_repo[repo.from_id] = repo.to_id
    return opt_repo


def _get_disabled_optional_repo():
    """
    Return a list of disabled optional repositories available on the system.
    """
    opt_repos = _get_list_of_optional_repos()
    repos_blacklist = []
    for repos in api.consume(RepositoriesFacts):
        for repo_file in repos.repositories:
            for repo in repo_file.data:
                if repo.repoid in opt_repos and not repo.enabled:
                    repos_blacklist.append(opt_repos[repo.repoid])
    return repos_blacklist


def process():
    # blacklist CRB repo if optional repo is not enabled
    reposid_blacklist = _get_disabled_optional_repo()
    if reposid_blacklist:
        api.current_logger().info("The optional repository is not enabled. Blacklisting the CRB repository.")
        api.produce(RepositoriesBlacklisted(repoids=[reposid_blacklist]))
