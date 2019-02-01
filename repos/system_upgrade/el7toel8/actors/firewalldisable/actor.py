from leapp.actors import Actor
from leapp.models import FirewallDecisionM, CheckResult, FirewallsFacts, Inhibitor
from leapp.tags import IPUWorkflowTag, ApplicationsPhaseTag
from leapp.libraries.stdlib import call


class FirewallDisable(Actor):
    """
    Stops and Disable FirewallD and/or IPTables.

    FirewallD and/or IPTables are services not supported during Upgrade process and they need to be
    stopped and disabled, so the daemons are not started after boot into Leapp provided initramfs.
    """

    name = 'firewalld_disable'
    consumes = (FirewallDecisionM, FirewallsFacts)
    produces = (CheckResult, Inhibitor)
    tags = (IPUWorkflowTag, ApplicationsPhaseTag,)

    def stop_firewalld(self):
        ''' Stop FirewallD '''
        call(['systemctl', 'stop', 'firewalld'])

    def disable_firewalld(self):
        ''' Disable FirewallD '''
        self.stop_firewalld()
        call(['systemctl', 'disable', 'firewalld'])

    def save_iptables(self):
        ''' Save IPTables '''
        f = open('iptables_bck_workfile', 'w')
        ret = call(['iptables-save'])
        for line in ret:
            f.write(line+'\n')
        f.close()

    def stop_iptables(self):
        ''' Stop IPTables '''
        call(['systemctl', 'stop', 'iptables'])

    def flush_iptables(self):
        ''' Flush rules '''
        call(['iptables', '-F'])

    def disable_iptables(self):
        ''' Save, stop and disable IPTables '''
        self.save_iptables()
        self.flush_iptables()
        self.stop_iptables()
        call(['systemctl', 'disable', 'iptables'])

    def process(self):
        ''' based on a decision maker Actor, it disables firewall services '''
        self.log.info("Starting to get decision on FirewallD.")
        for decision in self.consume(FirewallDecisionM):
            if decision.disable_choice == 'Y':
                self.log.info("Disabling Firewall.")
                for facts in self.consume(FirewallsFacts):
                    if facts.iptables.enabled:
                        self.log.info("- IPTables.")
                        self.disable_iptables()
                        break
                    elif facts.firewalld.enabled:
                        self.log.info("- FirewallD.")
                        self.disable_firewalld()
                        break
                    else:
                        continue

                self.log.info("Firewalls are disabled.")
                self.produce(
                   CheckResult(
                       severity='Info',
                       result='Pass',
                       summary='Firewalls are disabled',
                       details='FirewallD and/or IPTables services are disabled.',
                       solutions=None
                       ))
                return
            elif decision.disable_choice == 'N':
                self.log.info("Interrupting the upgrade process due the current user choice to take care for Firewall manually.")
                return
            elif decision.disable_choice == 'S':
                self.log.info("Skipping - all should be disabled.")
                return
        else:
            self.log.info("Interrupting: There was nothing to consume regarding the Firewall decision.")
            self.produce(
                Inhibitor(
                    summary='No message to consume',
                    details='No decision message to consume.',
                    solutions=None
                    ))
            return
