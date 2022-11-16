from leapp.actors import Actor
from leapp.libraries.actor import checksystemdservicetasks
from leapp.models import SystemdServicesTasks
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag


class CheckSystemdServicesTasks(Actor):
    """
    Inhibit the upgrade if SystemdServicesTasks tasks are in conflict

    SystemdServicesTasks messages with conflicting requested service states
    could be produced. For example a service could be requested to be both
    - enabled and disabled. This actor inhibits upgrade in such cases.

    Note: We expect that SystemdServicesTasks could be produced even after the
    TargetTransactionChecksPhase (e.g. during the ApplicationPhase). The
    purpose of this actor is to report collisions in case we can already detect
    them. In case of conflicts caused by messages produced later we just log
    the collisions and the services will end up disabled.
    """

    name = 'check_systemd_services_tasks'
    consumes = (SystemdServicesTasks,)
    produces = (Report,)
    tags = (TargetTransactionChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checksystemdservicetasks.check_conflicts()
