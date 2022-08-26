from leapp.actors import Actor
from leapp.libraries.actor import scansystemdsource
from leapp.models import SystemdBrokenSymlinksSource, SystemdServicesInfoSource, SystemdServicesPresetInfoSource
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanSystemdSource(Actor):
    """
    Provides info about systemd on the source system

    The provided info includes information about:
    - vendor presets of services
    - systemd service files, including their state
    - broken systemd symlinks

    There is an analogous actor :class:`ScanSystemdTarget` for target system.
    """

    name = 'scan_systemd_source'
    consumes = ()
    produces = (SystemdBrokenSymlinksSource, SystemdServicesInfoSource, SystemdServicesPresetInfoSource)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scansystemdsource.scan()
