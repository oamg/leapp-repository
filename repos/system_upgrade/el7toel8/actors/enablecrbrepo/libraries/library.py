from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import UsedTargetRepositories


CRB_REPOID = 'codeready-builder-for-rhel-8-x86_64-rpms'


def _is_crb_used():
    # the UsedTargetRepositories has to be set always, by design of IPU
    used_repos = next(api.consume(UsedTargetRepositories), None)
    for repo in used_repos.repos:
        if repo.repoid == CRB_REPOID:
            return True
    return False


def process():
    if _is_crb_used():
        try:
            run(['subscription-manager', 'repos', '--enable', CRB_REPOID])
        except CalledProcessError as e:
            api.current_logger().error('Cannot enable CRB repository: %s', str(e))
