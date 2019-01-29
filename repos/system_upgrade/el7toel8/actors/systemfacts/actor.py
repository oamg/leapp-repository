from leapp.actors import Actor
from leapp.libraries.actor import systemfacts
from leapp.models import SysctlVariablesFacts, ActiveKernelModulesFacts, UsersFacts, GroupsFacts, RepositoriesFacts, \
    SELinuxFacts, FirewallsFacts
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class SystemFactsActor(Actor):
    name = 'system_facts'
    description = 'Actor collecting facts about the system like Kernel Modules, Sysctl variables, Users, etc.'
    consumes = ()
    produces = (SysctlVariablesFacts,
                ActiveKernelModulesFacts,
                UsersFacts,
                GroupsFacts,
                RepositoriesFacts,
                SELinuxFacts,
                FirewallsFacts)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        self.produce(systemfacts.get_sysctls_status())
        self.produce(systemfacts.get_active_kernel_modules_status(self.log))
        self.produce(systemfacts.get_system_users_status())
        self.produce(systemfacts.get_system_groups_status())
        self.produce(systemfacts.get_repositories_status())
        self.produce(systemfacts.get_selinux_status())
        self.produce(systemfacts.get_firewalls_status())
