from leapp.actors import Actor
from leapp.models import FirewallsFacts, FirewallDecisionM, CheckResult
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag, ExperimentalTag
from leapp.dialogs import Dialog
from leapp.dialogs.components import BooleanComponent


class FirewallDecision(Actor):
    name = 'firewalld_decision'
    description = 'Firewall disable decision maker actor (pre-reboot) (check phase).'
    consumes = (FirewallsFacts,)
    produces = (FirewallDecisionM, CheckResult,)
    tags = (IPUWorkflowTag, ChecksPhaseTag, ExperimentalTag,)
    dialogs = (Dialog(
                scope='continue_fw',
                reason=
                    'FirewallD and/or IPTables are not supported by the upgrade process!\n'
                    'Please choose whether you would like to proceed and let the upgrade\n'
                    'disable the firewall. Answering \'N\' will stops the upgrade process',
                title='FirewallD and/or IPTables needs to be shutdown, please, confirm!',
                components=(
                    BooleanComponent(
                        key='continue_fw',
                        label='Shall the upgrade process disable the firewall',
                        default=False
                        ),),),)

    def process(self):
        self.log.info("Starting to get FirewallD decision.")
        for facts in self.consume(FirewallsFacts):
            # FIXME: checked only whether services are disabled. But in case
            # + there is another service/proces/... that starts firewalls during
            # + boot we will not catch it in this way. Shouldn't we check and
            # + print warning message in case the firewalls are active but
            # + services are disabled? To reflect possible risk, e.g. that user
            # + will not be able to connect to the upgraded system through ssh.
            # + Fix it later.
            if facts.firewalld.enabled or facts.iptables.enabled:
                answer = self.request_answers(self.dialogs[0]).get('continue_fw', False)
                self.produce(FirewallDecisionM(disable_choice='Y' if answer else 'N'))
                if not answer:
                    self.produce(
                        CheckResult(
                            severity='Error',
                            result='Fail',
                            summary='Firewall interrupts upgrade process request',
                            details='SA user chose to interrupt the upgrade.',
                            solutions=None
                            ))
                return
            else:
                # FIXME: See the fixme above
                self.log.info("Firewall is disabled. Nothing to decide.")
                self.produce(FirewallDecisionM(disable_choice='S'))
                self.produce(
                     CheckResult(
                        severity='Info',
                        result='Pass',
                        summary='Firewall disabled',
                        details='Firewall service is disabled.',
                        solutions=None
                        ))
                return
        else:
            self.log.info("No message to consume for the Firewall decision. Quitting..")
        return
