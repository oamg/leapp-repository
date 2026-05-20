from leapp.actors import Actor
from leapp.libraries.actor.checkfstabapifsoverride import check_fstab_api_fs_override
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckFstabApiFsOverride(Actor):
    """
    Inhibit upgrade if /etc/fstab contains invalid entries for pseudo-filesystem mountpoints.

    Paths like /proc, /sys, /dev/shm, /run are managed by the kernel and
    systemd and have specific requirements for their fstab entries. Defining
    them with block devices (via /dev/*, UUID=, LABEL=, etc.) or wrong
    filesystem types has been invalid since RHEL 7, but such configurations
    are typically ignored during normal boot. During the upgrade, these entries
    are applied as configured, which may lead to failures. This actor ensures
    users correct these entries before proceeding.
    """
    name = 'check_fstab_api_fs_override'
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        check_fstab_api_fs_override()
