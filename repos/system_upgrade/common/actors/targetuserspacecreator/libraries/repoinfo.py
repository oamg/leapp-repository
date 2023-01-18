from collections import defaultdict

from leapp.libraries.common import repofileutils
from leapp.libraries.stdlib import api
from leapp.models import TargetRepositories

DEFAULT_RHSM_REPOFILE = '/etc/yum.repos.d/redhat.repo'

REPO_KIND_RHUI = 'rhui'
REPO_KIND_RHSM = 'rhsm'
REPO_KIND_CUSTOM = 'custom'


class _RequestedRepoIDs(object):
    def __init__(self):
        self.rhel_repos = set()
        self.custom_repos = set()

    @property
    def combined(self):
        return self.rhel_repos | self.custom_repos


def _get_requested_repo_ids():
    """
    Get all requested target repositories.
    """
    result = _RequestedRepoIDs()
    for msg in api.consume(TargetRepositories):
        result.rhel_repos.update({r.repoid for r in msg.rhel_repos})
        result.custom_repos.update({r.repoid for r in msg.custom_repos})
    return result


class RepositoryInformation(object):
    def __init__(self, context, cloud_repo=None):
        self.repos = []
        self.rfiles = []
        self.mapped = defaultdict(list)
        self.repo_type_map = defaultdict(set)
        self._target_repo_ids = _get_requested_repo_ids()
        self._load_repofiles(context=context, cloud_repo=cloud_repo)

    def _load_repofiles(self, context, cloud_repo=None):
        for rfile in repofileutils.get_parsed_repofiles(
                context=context,
                kind_resolve=resolve_repo_file_kind(cloud_repo)):
            self.add_file(rfile)

    @property
    def rhsm_repoids(self):
        return self.repo_type_map[REPO_KIND_RHSM]

    @property
    def rhui_repoids(self):
        return self.repo_type_map[REPO_KIND_RHUI]

    @property
    def rhel_repoids(self):
        return self.rhsm_repoids | self.rhui_repoids

    @property
    def custom_repoids(self):
        return self.repo_type_map[REPO_KIND_CUSTOM]

    @property
    def missing_custom_repoids(self):
        return self._target_repo_ids.custom_repos - self.custom_repoids

    @property
    def target_repoids(self):
        return (self._target_repo_ids.custom_repos & self.custom_repoids) | (
            self._target_repo_ids.rhel_repos & self.rhel_repoids)

    def add_file(self, rfile):
        self.rfiles.append(rfile)
        for repo in rfile.data:
            self.add(repo)

    def add(self, repo):
        self.repos.append(repo)
        self.mapped[repo.repoid].append(repo)
        self.repo_type_map[repo.kind].add(repo.repoid)

    @property
    def duplicated_repoids(self):
        return {k: v for k, v in self.mapped.items() if len(v) > 1}


def resolve_repo_file_kind(cloud_repo):
    def resolver(path):
        if path == DEFAULT_RHSM_REPOFILE:
            return REPO_KIND_RHSM
        if cloud_repo and path == cloud_repo:
            return REPO_KIND_RHUI
        return REPO_KIND_CUSTOM
    return resolver
