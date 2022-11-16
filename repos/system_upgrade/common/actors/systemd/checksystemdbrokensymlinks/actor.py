from leapp.actors import Actor
from leapp.libraries.actor import checksystemdbrokensymlinks
from leapp.models import SystemdBrokenSymlinksSource, SystemdServicesInfoSource
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSystemdBrokenSymlinks(Actor):
    """
    Check whether some systemd symlinks are broken

    If some systemd symlinks are broken, report them but do not inhibit the
    upgrade. The symlinks broken already before the upgrade will not be
    handled by the upgrade process anyhow. Two different reports are created:
    - symlinks which have the same filename as an existing enabled systemd
      service (the symlink doesn't point to an existing unit file, but the
      service is enabled)
    - broken symlinks which names do not correspond with any existing systemd
      unit file (typically when the service is removed but not disabled
      correctly)
    """

    name = 'check_systemd_broken_symlinks'
    consumes = (SystemdBrokenSymlinksSource, SystemdServicesInfoSource)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checksystemdbrokensymlinks.process()
