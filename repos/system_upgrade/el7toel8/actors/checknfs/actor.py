from leapp.actors import Actor
from leapp.models import StorageInfo, CheckResult
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNfs(Actor):
    name = "check_nfs"
    description = "Check if NFS filesystem is in use. If yes, inhibit the upgrade process."
    consumes = (StorageInfo,)
    produces = (CheckResult,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def error(self):
        self.produce(CheckResult(
            severity="Error",
            result="Fail",
            summary="NFS is not supported.",
            details="",
            solutions="Don't use NFS."))

    def process(self):
        for storage in self.consume(StorageInfo):
            # Check fstab
            for fstab in storage.fstab:
                if fstab.fs_vfstype == "nfs":
                    self.error()

            # Check mount
            for mount in storage.mount:
                if mount.tp == "nfs":
                    self.error()

            # Check selinux-mount
            for systemdmount in storage.systemdmount:
                if systemdmount.fs_type == "nfs":
                    self.error()
