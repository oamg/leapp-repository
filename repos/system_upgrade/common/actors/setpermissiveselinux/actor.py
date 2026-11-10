from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.actor.setpermissiveselinux import selinux_set_permissive
from leapp.models import SelinuxPermissiveDecision
from leapp.reporting import create_report, Report
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class SetPermissiveSelinux(Actor):
    """
    Set SELinux mode.

    In order to proceed with Upgrade process, SELinux should be set into permissive mode if it was
    in enforcing mode.
    """

    name = 'set_permissive_se_linux'
    consumes = (SelinuxPermissiveDecision,)
    produces = (Report,)
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        for decision in self.consume(SelinuxPermissiveDecision):
            if decision.set_permissive:
                success, err_msg = selinux_set_permissive()
                if not success:
                    # FIXME: add an "action required" flag later
                    create_report([
                        reporting.Title('Could not set SElinux into permissive mode'),
                        reporting.Summary(
                            'Leapp could not set SELINUX=permissive in /etc/selinux/config: {}. '
                            'The upgraded system still boots with SElinux in permissive mode because '
                            'leapp adds the enforcing=0 kernel argument.'.format(err_msg)
                        ),
                        reporting.Remediation(hint=(
                            'Check why /etc/selinux/config could not be modified, for example whether '
                            'the file is immutable ("lsattr /etc/selinux/config"). The configuration file '
                            'still sets SELINUX=enforcing, so SElinux will be in enforcing mode as soon as '
                            'the enforcing=0 kernel argument is removed. Remove it only after checking that '
                            'there are no SElinux related warnings on the upgraded system.'
                        )),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY]),
                        reporting.Groups([reporting.Groups.FAILURE]),
                        reporting.RelatedResource('file', '/etc/selinux/config')
                    ])
                    self.log.critical('Could not set SElinux into permissive mode: %s.' % err_msg)
