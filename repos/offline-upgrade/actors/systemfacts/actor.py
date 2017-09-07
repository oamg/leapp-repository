from leapp.actors import Actor
from leapp.libraries.actor import systemfacts
from leapp.models import SystemFacts
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class SystemFactsActor(Actor):
    name = 'system_facts'
    description = 'Actor collecting facts about the system like Kernel Modules, Sysctl variables, Users, etc.'
    consumes = ()
    produces = (SystemFacts,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        self.produce(SystemFacts(
            sysctl_variables=systemfacts.get_sysctls(),
            kernel_modules=systemfacts.get_active_kernel_modules(self.log),
            users=systemfacts.get_system_users(),
            groups=systemfacts.get_system_groups(),
            repositories=systemfacts.get_repositories(),
            selinux=systemfacts.get_selinux_status(),
            firewalls=systemfacts.get_firewalls_status()
        ))
