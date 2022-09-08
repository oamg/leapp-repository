from leapp.actors import Actor
from leapp.libraries.actor import setsystemdservicesstate
from leapp.models import SystemdServicesTasks
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class SetSystemdServicesState(Actor):
    """
    According to input messages sets systemd services states on the target system
    """

    name = 'set_systemd_services_state'
    consumes = (SystemdServicesTasks,)
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        setsystemdservicesstate.process()
