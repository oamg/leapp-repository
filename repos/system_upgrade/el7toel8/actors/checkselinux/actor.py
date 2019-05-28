from leapp.actors import Actor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.models import SELinuxFacts, SelinuxPermissiveDecision, SelinuxRelabelDecision
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_generic


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
                report_generic(
                    title='SElinux disabled in configuration file but currently enabled',
                    summary='This message is to inform user about non-standard SElinux configuration.',
                    severity='low')
            report_generic(
                title='SElinux disabled',
                summary='SElinux disabled, continuing...',
                severity='low')
            return

        if conf_status in ('enforcing', 'permissive'):
            self.produce(SelinuxRelabelDecision(
                set_relabel=True))
            report_generic(
                title='Schedule SElinux relabeling',
                summary='Schedule SElinux relabeling as the status was permissive/enforcing.',
                severity='low')

        if conf_status == 'enforcing':
            self.produce(SelinuxPermissiveDecision(
                set_permissive=True))
            report_generic(
                title='SElinux will be set to permissive mode',
                summary='SElinux will be set to permissive mode as it was in enforcing mode.',
                severity='low')
