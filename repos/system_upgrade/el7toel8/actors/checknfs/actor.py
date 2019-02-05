from leapp.actors import Actor
from leapp.models import StorageInfo, Inhibitor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNfs(Actor):
    name = "check_nfs"
    description = "Check if NFS filesystem is in use. If yes, inhibit the upgrade process."
    consumes = (StorageInfo,)
    produces = (Inhibitor,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def inhibit(self, details):
        self.produce(Inhibitor(
            summary="NFS is not supported.",
            details=details,
            solutions="Please consider not using NFS."))

    def process(self):
        for storage in self.consume(StorageInfo):
            # Check fstab
            for fstab in storage.fstab:
                if fstab.fs_vfstype == "nfs":
                    self.inhibit("Discovered NFS entry in the fstab.")

            # Check mount
            for mount in storage.mount:
                if mount.tp == "nfs":
                    self.inhibit("Discovered NFS entry in the mount.")

            # Check selinux-mount
            for systemdmount in storage.systemdmount:
                if systemdmount.fs_type == "nfs":
                    self.inhibit("Discovered NFS entry in the systemd-mount.")
