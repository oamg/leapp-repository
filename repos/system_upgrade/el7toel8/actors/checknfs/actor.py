from leapp.actors import Actor
from leapp.models import StorageInfo, Inhibitor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNfs(Actor):
    """
    Check if NFS filesystem is in use. If yes, inhibit the upgrade process.

    Actor looks for NFS in the following sources: /ets/fstab, mount and systemd-mount.
    If there is NFS in any of the mentioned sources, actors inhibits the upgrade.
    """
    name = "check_nfs"
    consumes = (StorageInfo,)
    produces = (Inhibitor,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        details = "NFS is currently not supported by the inplace upgrade.\n" \
                  "We have found NFS usage at the following locations:\n"
        nfs_found = False

        for storage in self.consume(StorageInfo):
            # Check fstab
            for fstab in storage.fstab:
                if fstab.fs_vfstype == "nfs":
                    nfs_found = True
                    details += "- One or more NFS entries in /etc/fstab\n"
                    break

            # Check mount
            for mount in storage.mount:
                if mount.tp == "nfs":
                    nfs_found = True
                    details += "- Currently mounted NFS shares\n"
                    break

            # Check systemd-mount
            for systemdmount in storage.systemdmount:
                if systemdmount.fs_type == "nfs":
                    nfs_found = True
                    details += "- One or more configured NFS mounts in systemd-mount\n"
                    break

        if nfs_found:
            self.produce(Inhibitor(
                summary="Unsupported NFS usage found.",
                details=details,
                solutions="Please consider not using NFS."))

