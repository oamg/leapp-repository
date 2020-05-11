from leapp.actors import Actor
from leapp.libraries.actor.checkbootavailspace import (
    check_avail_space_on_boot,
    get_avail_bytes_on_boot,
)
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckBootAvailSpace(Actor):
    """
    Check if at least 100Mib of available space on /boot. If not, inhibit the upgrade process.

    Rationale for the requirement of 100MiB:
    - Before reboot into initramfs, the CopyInitramfsToBoot actor copies kernel and initramfs to
      /boot, together worth of 66MiB.
    - After booting into initramfs, the RemoveBootFiles actor removes the copied kernel and
      initramfs from /boot.
    - The DnfShellRpmUpgrade installs a new kernel-core package which puts additional 54MiB of data
      to /boot.
    - Even though the available space needed at the time of writing this actor is 66MiB, the
      additional 100-66=34MiB is a leeway for potential growth of the kernel or initramfs in size.
    """

    name = 'check_boot_avail_space'
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_avail_space_on_boot(get_avail_bytes_on_boot)
