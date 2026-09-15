from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.common.dnflibs import dnfplugin
from leapp.models import DNFWorkaround, TargetUserSpaceInfo
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class ApplyTransactionWorkarounds(Actor):
    """
    Executes registered workaround scripts on the system before the upgrade transaction
    """

    name = 'applytransactionworkarounds'
    consumes = (DNFWorkaround, TargetUserSpaceInfo)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)
        if not target_userspace_info:
            raise StopActorExecutionError("Did not receive the expected TargetUserSpaceInfo message")

        # bind mount installroot so that the workaround can e.g. import gpg keys there
        bind_mounts = ['/:/installroot']
        with mounting.NspawnActions(base_dir=target_userspace_info.path, binds=bind_mounts) as context:
            dnfplugin.apply_workarounds(None, context)
