from leapp.actors import Actor
from leapp.libraries.actor.removeoldpammodulesapply import comment_modules, read_file
from leapp.libraries.common.pam import PAM
from leapp.models import RemovedPAMModules
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class RemoveOldPAMModulesApply(Actor):
    """
    Remove old PAM modules that are no longer available in RHEL-8 from
    PAM configuration to avoid system lock out.
    """

    name = 'removed_pam_modules_apply'
    consumes = (RemovedPAMModules,)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        for model in self.consume(RemovedPAMModules):
            for path in PAM.files:
                content = read_file(path)
                if not content:  # Nothing to do if no content?
                    continue

                with open(path, 'w') as f:
                    f.write(comment_modules(model.modules, content))
            break
