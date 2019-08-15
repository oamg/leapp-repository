from leapp.actors import Actor
from leapp.libraries.actor import systemfacts
from leapp.models import SysctlVariablesFacts, ActiveKernelModulesFacts, UsersFacts, GroupsFacts, RepositoriesFacts, \
    SELinuxFacts, FirewallsFacts, FirmwareFacts
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class SystemFactsActor(Actor):
    """
    Provides data about many facts from system.

    After collecting data from multiple tools, messages with relevant data will be produced to
    describe:
      - Sysctl variables;
      - Active Linux Kernel Modules;
      - Users;
      - Groups;
      - Package repositories;
      - SELinux status;
      - Firewalls status.
    """

    name = 'system_facts'
    consumes = ()
    produces = (SysctlVariablesFacts,
                ActiveKernelModulesFacts,
                UsersFacts,
                GroupsFacts,
                RepositoriesFacts,
                SELinuxFacts,
                FirewallsFacts,
                FirmwareFacts)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        self.produce(systemfacts.get_sysctls_status())
        self.produce(systemfacts.get_active_kernel_modules_status(self.log))
        self.produce(systemfacts.get_system_users_status())
        self.produce(systemfacts.get_system_groups_status())
        self.produce(systemfacts.get_repositories_status())
        self.produce(systemfacts.get_selinux_status())
        self.produce(systemfacts.get_firewalls_status())
        self.produce(systemfacts.get_firmware())
