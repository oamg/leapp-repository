from leapp.actors import Actor
from leapp.libraries.actor import check_first_partition_offset
from leapp.models import FirmwareFacts, GRUBDevicePartitionLayout
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckFirstPartitionOffset(Actor):
    """
    Check whether the first partition starts at the offset >=1MiB.

    The alignment of the first partition plays role in disk access speeds. Older tools placed the start of the first
    partition at cylinder 63 (due to historical reasons connected to the INT13h BIOS API). However, grub core
    binary is placed before the start of the first partition, meaning that not enough space causes bootloader
    installation to fail. Modern partitioning tools place the first partition at >= 1MiB (cylinder 2048+).
    """

    name = 'check_first_partition_offset'
    consumes = (FirmwareFacts, GRUBDevicePartitionLayout,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        check_first_partition_offset.check_first_partition_offset()
