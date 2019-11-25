from leapp.actors import Actor
from leapp.models import TransactionCompleted
from leapp.tags import RPMUpgradePhaseTag, IPUWorkflowTag, ExperimentalTag
from leapp.libraries.stdlib import api, run, CalledProcessError


class GrubbyDebug(Actor):
    """
    Temporary experimental debug actor to add "set -x" option in grubby scripts
    """

    name = 'grubby_debug'
    consumes = (TransactionCompleted,)
    produces = ()
    tags = (ExperimentalTag, RPMUpgradePhaseTag, IPUWorkflowTag, )

    def process(self):
        try:
            run(["sed", "-i", r"/^\#\!\/bin\/bash/aset -x", "/usr/libexec/grubby/grubby-bls"])
        except CalledProcessError:
            api.current_logger().warning('Failed to activate debug mode in grubby-bls', exc_info=True)
        try:
            run(["sed", "-i", r"/^\#\!\/bin\/bash/aset -x", "/usr/libexec/grubby/grubby"])
        except CalledProcessError:
            api.current_logger().warning('Failed to activate debug mode in grubby', exc_info=True)
