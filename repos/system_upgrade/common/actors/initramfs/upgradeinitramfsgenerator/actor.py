from leapp.actors import Actor
from leapp.libraries.actor import upgradeinitramfsgenerator
from leapp.models import RequiredUpgradeInitramPackages  # deprecated
from leapp.models import UpgradeDracutModule  # deprecated
from leapp.models import (
    BootContent,
    FIPSInfo,
    TargetOSInstallationImage,
    TargetUserSpaceInfo,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UsedTargetRepositories
)
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class UpgradeInitramfsGenerator(Actor):
    """
    Creates the upgrade initramfs

    Creates an initram disk within a systemd-nspawn container using the target
    system userspace, including new kernel. The creation of the initram disk
    can be influenced with the UpgradeInitramfsTasks message (e.g. specifying
    what files or dracut modules should be installed in the upgrade initramfs)

    See the UpgradeInitramfsTasks model for more details.
    """

    name = 'upgrade_initramfs_generator'
    consumes = (
        FIPSInfo,
        RequiredUpgradeInitramPackages,  # deprecated
        TargetOSInstallationImage,
        TargetUserSpaceInfo,
        TargetUserSpaceUpgradeTasks,
        UpgradeDracutModule,  # deprecated
        UpgradeInitramfsTasks,
        UsedTargetRepositories,
    )
    produces = (BootContent,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        upgradeinitramfsgenerator.process()
