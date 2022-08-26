from leapp.actors import Actor
from leapp.libraries.actor import scansystemdtarget
from leapp.models import SystemdBrokenSymlinksTarget, SystemdServicesInfoTarget, SystemdServicesPresetInfoTarget
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class ScanSystemdTarget(Actor):
    """
    Provides info about systemd on the source system

    The provided info includes information about:
    - vendor presets of services
    - systemd service files, including their state
    - broken systemd symlinks

    There is an analogous actor :class:`ScanSystemdSource` for source system

    The actor ignore errors (errors are logged, but do not stop the upgrade).
    If some data cannot be obtained, particular message is not produced.
    Actors are expected to check whether the data is available.
    """
    name = 'scan_systemd_target'
    consumes = ()
    produces = (SystemdBrokenSymlinksTarget, SystemdServicesInfoTarget, SystemdServicesPresetInfoTarget)
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        scansystemdtarget.scan()
