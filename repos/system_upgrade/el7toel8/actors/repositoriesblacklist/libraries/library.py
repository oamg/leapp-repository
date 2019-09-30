from leapp.libraries.stdlib import api
from leapp.models import  RepositoriesBlacklisted, RepositoriesFacts, RepositoriesMap


def get_list_of_optional_repos():
    """
        Returns a dictionary with these fields:
            key = from_id
            value = to_id
    """
    opt_repo = {}
    repo_map = next(api.consume(RepositoriesMap), None)
    for repo in repo_map:
        if repo.from_id.endswith('optional-rpm'):
            opt_repo[repo.from_id] = repo.to_id
    return opt_repo


def get_disabled_optional_repo():
    """
        Returns a list os repos which is part of optional repos and is disabled
    """
    opt_repos = get_list_of_optional_repos()
    repos_blacklist = []
    for repos in api.consume(RepositoriesFacts):
        for repo_file in repos.repositories:
            for repo in repo_file.data:
                if repo.repoid in opt_repos and not repo.enabled:
                    repos_blacklist.append(opt_repos[repo.repoid])
    return repos_blacklist


def process():
    # blacklist CRB repo if optional repo is not enabled
    reposid_blacklist = get_disabled_optional_repo()
    if reposid_blacklist:
        api.current_logger().info("The optional repository is not enabled. Blacklisting the CRB repository.")
        api.produce(RepositoriesBlacklisted(repoids=[reposid_blacklist]))
