from leapp.actors import Actor
from leapp.models import FirewalldDirectConfig, FirewalldGlobalConfig, FirewallsFacts, RpmTransactionTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class FirewalldIptablesModules(Actor):
    """
    This actor cause kernel-modules-extra to be installed if firewalld is using
    iptables.
    """

    name = 'firewalld_iptables_modules'
    consumes = (FirewallsFacts, FirewalldGlobalConfig, FirewalldDirectConfig)
    produces = (RpmTransactionTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        # If firewalld is not enabled then don't bother the user about its
        # configuration.
        for facts in self.consume(FirewallsFacts):
            if not facts.firewalld.enabled:
                return

        flag = False

        for config in self.consume(FirewalldGlobalConfig):
            if config.firewallbackend == "iptables":
                flag = True
                break

        for config in self.consume(FirewalldDirectConfig):
            if config.has_permanent_configuration:
                flag = True
                break

        if flag:
            self.produce(RpmTransactionTasks(to_install=['kernel-modules-extra']))
