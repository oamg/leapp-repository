from leapp.actors import Actor
from leapp.libraries.actor import adjustlocalrepos
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api
from leapp.models import (
    TargetOSInstallationImage,
    TargetUserSpaceInfo,
    TMPTargetRepositoriesFacts,
    UsedTargetRepositories
)
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(TMPTargetRepositoriesFacts)
class AdjustLocalRepos(Actor):
    """
    Adjust local repositories to the target user-space container.

    Changes the path of local file urls (starting with 'file://') for 'baseurl' and
    'mirrorlist' fields to the container space for the used repositories. This is
    done by prefixing host root mount bind ('/installroot') to the path. It ensures
    that the files will be accessible from the container and thus proper functionality
    of the local repository.
    """

    name = 'adjust_local_repos'
    consumes = (TargetOSInstallationImage,
                TargetUserSpaceInfo,
                TMPTargetRepositoriesFacts,  # deprecated
                UsedTargetRepositories)
    produces = ()
    tags = (IPUWorkflowTag, TargetTransactionChecksPhaseTag)

    def process(self):
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)
        used_target_repos = next(self.consume(UsedTargetRepositories), None)
        target_repos_facts = next(self.consume(TMPTargetRepositoriesFacts), None)
        target_iso = next(self.consume(TargetOSInstallationImage), None)

        if not all([target_userspace_info, used_target_repos, target_repos_facts]):
            api.current_logger().error("Missing required information to proceed!")
            return

        target_repos_facts = target_repos_facts.repositories
        iso_repoids = set(repo.repoid for repo in target_iso.repositories) if target_iso else set()
        used_target_repoids = set(repo.repoid for repo in used_target_repos.repos)

        with mounting.NspawnActions(base_dir=target_userspace_info.path) as context:
            adjustlocalrepos.process(context, target_repos_facts, iso_repoids, used_target_repoids)
