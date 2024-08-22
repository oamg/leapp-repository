from leapp.actors import Actor
from leapp.libraries.actor import checkgrubenvtofile
from leapp.models import ConvertGrubenvTask, FirmwareFacts, HybridImageAzure
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckGrubenvToFile(Actor):
    """
    Check whether grubenv is a symlink on Azure hybrid images using BIOS.

    Azure images provided by Red Hat aim for hybrid (BIOS/EFI) functionality,
    however, currently GRUB is not able to see the "grubenv" file if it is a
    symlink to a different partition (default on EFI with grub2-efi pkg
    installed) and fails on BIOS systems.

    These images have a default relative symlink to EFI partition even when
    booted using BIOS and in such cases GRUB is not able to find "grubenv" and
    fails to get the kernel cmdline options resulting in system failing to boot
    after upgrade.

    The symlink needs to be converted to a normal file with the content of
    grubenv on the EFI partition in case the system is using BIOS and running
    on the Azure cloud. This action is reported in the preupgrade phase.

    """

    name = 'check_grubenv_to_file'
    consumes = (FirmwareFacts, HybridImageAzure,)
    produces = (ConvertGrubenvTask, Report)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkgrubenvtofile.process()
