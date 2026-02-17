from leapp.actors import Actor
from leapp.libraries.actor import enablelogrotatetimer
from leapp.models import SystemdServicesInfoTarget, SystemdServicesTasks
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class EnableLogrotateTimer(Actor):
    """
    Enable logrotate.timer on the target system after upgrade

    The logrotate.timer systemd timer unit replaces the traditional cron-based
    logrotate execution used in RHEL 8. This actor ensures the timer is enabled
    after the in-place upgrade is complete.
    """

    name = 'enable_logrotate_timer'
    consumes = (SystemdServicesInfoTarget,)
    produces = (SystemdServicesTasks,)
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        enablelogrotatetimer.process()
