from leapp.actors import Actor
from leapp.libraries.actor import scan_default_initramfs as scan_default_initramfs_lib
from leapp.models import DefaultInitramfsInfo, DefaultSourceBootEntry
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanDefaultInitramfs(Actor):
    """
    Scan details of the default boot entry's initramfs image.

    Information such as used dracut modules are collected.
    """

    name = 'scan_default_initramfs'
    consumes = (DefaultSourceBootEntry,)
    produces = (DefaultInitramfsInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scan_default_initramfs_lib.scan_default_initramfs()
