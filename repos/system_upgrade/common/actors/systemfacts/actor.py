from leapp.actors import Actor
from leapp.libraries.actor import systemfacts
from leapp.libraries.common.config import architecture
from leapp.models import (
    ActiveKernelModulesFacts,
    DefaultGrubInfo,
    FirewallsFacts,
    FirmwareFacts,
    GroupsFacts,
    GrubCfgBios,
    Report,
    RepositoriesFacts,
    SELinuxFacts,
    SysctlVariablesFacts,
    UsersFacts
)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


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
    produces = (
        SysctlVariablesFacts,
        ActiveKernelModulesFacts,
        UsersFacts,
        GroupsFacts,
        RepositoriesFacts,
        SELinuxFacts,
        FirewallsFacts,
        FirmwareFacts,
        DefaultGrubInfo,
        GrubCfgBios,
        Report
    )
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

        if not architecture.matches_architecture(architecture.ARCH_S390X):
            self.produce(systemfacts.get_default_grub_conf())

        bios_grubcfg_details = systemfacts.get_bios_grubcfg_details()
        if bios_grubcfg_details:
            self.produce(bios_grubcfg_details)
