from leapp.actors import Actor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.models import SELinuxFacts, SelinuxPermissiveDecision, SelinuxRelabelDecision
from leapp.reporting import Report, create_report
from leapp import reporting


class CheckSelinux(Actor):
    """
    Check SELinux status and produce decision messages for further action.

    Based on SELinux status produces decision messages to relabeling and changing status if
    necessary
    """

    name = 'check_se_linux'
    consumes = (SELinuxFacts,)
    produces = (Report, SelinuxPermissiveDecision, SelinuxRelabelDecision)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):

        fact = next(self.consume(SELinuxFacts), None)
        if not fact:
            return

        enabled = fact.enabled
        conf_status = fact.static_mode

        if conf_status == 'disabled':
            if enabled:
                create_report([
                    reporting.Title('SElinux disabled in configuration file but currently enabled'),
                    reporting.Summary('This message is to inform user about non-standard SElinux configuration.'),
                    reporting.Severity(reporting.Severity.LOW),
                    reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY])
                ])
            create_report([
                reporting.Title('SElinux disabled'),
                reporting.Summary('SElinux disabled, continuing...'),
                reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY])
            ])
            return

        if conf_status in ('enforcing', 'permissive'):
            self.produce(SelinuxRelabelDecision(
                set_relabel=True))
            create_report([
                reporting.Title('SElinux relabeling has been scheduled'),
                reporting.Summary('SElinux relabeling has been scheduled as the status was permissive/enforcing.'),
                reporting.Severity(reporting.Severity.INFO),
                reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY])
            ])

        if conf_status == 'enforcing':
            self.produce(SelinuxPermissiveDecision(
                set_permissive=True))
            create_report([
                reporting.Title('SElinux will be set to permissive mode'),
                reporting.Summary('SElinux will be set to permissive mode. Current mode: enforcing. This action is '
                                  'required by the upgrade process'),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY])
            ])
