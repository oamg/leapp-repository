from leapp.actors import Actor
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.models import SelinuxRelabelDecision
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_generic, report_with_remediation


class ScheduleSeLinuxRelabeling(Actor):
    """
    Schedule SELinux relabelling.

    If SELinux status was set to permissive or enforcing, a relabelling is necessary.
    """

    name = 'schedule_se_linux_relabelling'
    consumes = (SelinuxRelabelDecision,)
    produces = (Report,)
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        for decision in self.consume(SelinuxRelabelDecision):
            if decision.set_relabel:
                try:
                    with open('/.autorelabel', 'w'):
                        pass
                    report_generic(
                        title='SElinux scheduled for relabelling',
                        summary='/.autorelabel file touched on root in order to schedule SElinux relabelling.',
                        severity='low',
                    )
                except OSError as e:
                    # FIXME: add an "action required" flag later
                    report_with_remediation(
                        title='Could not schedule SElinux for relabelling',
                        summary='./autorelabel file could not be created: {}.'.format(e),
                        remediation='Please set autorelabelling manually after the upgrade.',
                        severity='high'
                    )
                    self.log.critical('Could not schedule SElinux for relabelling: %s.' % e)
