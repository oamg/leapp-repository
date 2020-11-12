from leapp.actors import Actor
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.models import SelinuxRelabelDecision
from leapp.reporting import Report, create_report
from leapp import reporting


COMMON_REPORT_GROUPS = [reporting.Groups.SELINUX]

related = [reporting.RelatedResource('file', '/.autorelabel')]


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
                    create_report([
                        reporting.Title('SElinux scheduled for relabelling'),
                        reporting.Summary(
                            '/.autorelabel file touched on root in order to schedule SElinux relabelling.'),
                        reporting.Severity(reporting.Severity.INFO),
                        reporting.Groups(COMMON_REPORT_GROUPS),
                    ] + related)

                except EnvironmentError as e:
                    # FIXME: add an "action required" flag later
                    create_report([
                        reporting.Title('Could not schedule SElinux for relabelling'),
                        reporting.Summary('/.autorelabel file could not be created: {}.'.format(e)),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.Groups(COMMON_REPORT_GROUPS + [reporting.Groups.FAILURE]),
                        reporting.Remediation(
                            hint='Please set autorelabelling manually after the upgrade.'
                        ),
                    ] + related)
                    self.log.critical('Could not schedule SElinux for relabelling: %s.' % e)
