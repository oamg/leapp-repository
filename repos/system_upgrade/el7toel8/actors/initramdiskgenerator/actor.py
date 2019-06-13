from leapp.actors import Actor
from leapp.libraries.actor import initramgen
from leapp.models import (BootContent, RequiredUpgradeInitramPackages, TargetUserSpaceInfo, UpgradeDracutModule,
                          UsedTargetRepositories)
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class InitramDiskGenerator(Actor):
    """
    Creates the upgrade initram disk

    Creates an initram disk within a systemd-nspawn container using the target system userspace, including new kernel.
    The creation of the initram disk can be influenced with RequiredUpgradeInitramPackages and UpgradeDracutModule,
    which allow to specify additional packages to install in the target userspace and dracut modules to be included
    during the dracut execution.
    """

    name = 'initram_disk_generator'
    consumes = (RequiredUpgradeInitramPackages, TargetUserSpaceInfo, UpgradeDracutModule, UsedTargetRepositories)
    produces = (BootContent,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        initramgen.process()
