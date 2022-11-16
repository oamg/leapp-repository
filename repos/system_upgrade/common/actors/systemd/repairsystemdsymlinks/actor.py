from leapp.actors import Actor
from leapp.libraries.actor import repairsystemdsymlinks
from leapp.models import SystemdBrokenSymlinksSource, SystemdBrokenSymlinksTarget, SystemdServicesInfoSource
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class RepairSystemdSymlinks(Actor):
    """
    Fix broken or incorrect systemd symlinks

    Symlinks are handled in the following fashion, if the symlink points to:
        - a removed unit, such a symlink is deleted
        - a unit whose installation has been changed (e.g. changed WantedBy),
          such symlinks are fixed (re-enabled using systemctl)

    Symlinks that have been already broken before the in-place upgrade are ignored.
    """

    name = 'repair_systemd_symlinks'
    consumes = (SystemdBrokenSymlinksSource, SystemdBrokenSymlinksTarget, SystemdServicesInfoSource)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        repairsystemdsymlinks.process()
