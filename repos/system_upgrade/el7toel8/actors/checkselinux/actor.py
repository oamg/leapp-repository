from leapp.actors import Actor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.models import SELinuxFacts, CheckResult, SelinuxPermissiveDecision, SelinuxRelabelDecision


class CheckSelinux(Actor):
    name = 'check_se_linux'
    description = 'Check SElinux status and produce decision messages for further action'
    consumes = (SELinuxFacts,)
    produces = (CheckResult, SelinuxPermissiveDecision, SelinuxRelabelDecision)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def produce_info(self, result, summary, details, solution=None):
        self.produce(CheckResult(
             severity='Info',
             result=result,
             summary=summary,
             details=details,
             solutions=solution))

    def process(self):
        for fact in self.consume(SELinuxFacts):
            enabled = fact.enabled
            conf_status = fact.static_mode

        if conf_status == 'disabled':
            if enabled:
                self.produce_info('Pass', 'SElinux disabled in configuration file but currently enabled',
                                  'This message is to inform user about non-standard SElinux configuration')
            self.produce_info('Pass', 'SElinux disabled', 'SElinux disabled, continuing...')
            return

        if conf_status in ('enforcing', 'permissive'):
            self.produce(SelinuxRelabelDecision(
                set_relabel=True))
            self.produce_info('Fixed', 'Schedule SElinux relabeling',
                              'Schedule SElinux relabeling as the status was permissive/enforcing')

        if conf_status == 'enforcing':
            self.produce(SelinuxPermissiveDecision(
                set_permissive=True))
            self.produce_info('Fixed', 'SElinux will be set to permissive mode',
                              'SElinux will be set to permissive mode as it was in enforcing mode')

