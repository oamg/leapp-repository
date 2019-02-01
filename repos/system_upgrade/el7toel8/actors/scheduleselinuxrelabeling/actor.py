import sys

from leapp.actors import Actor
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.models import SelinuxRelabelDecision, FinalReport


class ScheduleSeLinuxRelabeling(Actor):
    """
    Schedule SELinux relabeling.

    If SELinux status was set to permissive or enforcing, a relabeling is necessary.
    """

    name = 'schedule_se_linux_relabelling'
    consumes = (SelinuxRelabelDecision,)
    produces = (FinalReport,)
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        for decision in self.consume(SelinuxRelabelDecision):
            if decision.set_relabel:
                try:
                    with open('/.autorelabel', 'w'):
                        pass
                except OSError as e:
                    self.produce(FinalReport(
                        severity='Error',
                        result='Fail',
                        summary='Could not schedule SElinux for relabelling',
                        details=e,))
                    self.log.critical('Could not schedule SElinux for relabelling: %s' % e)
