from leapp.actors import Actor
from leapp.libraries.actor import cleanupbootloaderentries
from leapp.models import MachineIdInfo, TransactionCompleted
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class CleanupBootloaderEntries(Actor):
    """
    Remove boot loader entries that don't match the current machine ID during conversion.

    Boot Loader Specification entry files are named
    ``/boot/loader/entries/<entry-token>-<kernel-version>.conf``, where the
    entry token defaults to ``/etc/machine-id``. When the current machine ID
    differs from the one used when the original OS kernels were installed,
    ``kernel-install remove`` (run from the kernel package scriptlets during the
    upgrade transaction) derives the entry path from the current machine ID and
    fails to remove the original entries, leaving them orphaned. The newly
    installed target kernel entry uses the current machine ID.

    This actor removes the entries whose file name doesn't contain the
    current machine ID. The target kernel is set as the default boot entry later
    by the force_default_boot_to_target_kernel_version actor.
    """

    name = 'cleanup_bootloader_entries'
    consumes = (MachineIdInfo, TransactionCompleted)
    produces = (Report,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        cleanupbootloaderentries.process()
