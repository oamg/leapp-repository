from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common.config import get_env
from leapp.models import StorageInfo
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNfs(Actor):
    """
    Check if NFS filesystem is in use. If yes, inhibit the upgrade process.

    Actor looks for NFS in the following sources: /ets/fstab, mount and systemd-mount.
    If there is NFS in any of the mentioned sources, actors inhibits the upgrade.
    """
    name = "check_nfs"
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        # if network in initramfs is enabled NFS inhibitors are redundant
        if get_env('LEAPP_DEVEL_INITRAM_NETWORK', None):
            return
        details = "NFS is currently not supported by the inplace upgrade.\n" \
                  "We have found NFS usage at the following locations:\n"

        def _is_nfs(a_type):
            return a_type.startswith('nfs') and a_type != 'nfsd'

        for storage in self.consume(StorageInfo):
            # Check fstab
            fstab_nfs_mounts = []
            for fstab in storage.fstab:
                if _is_nfs(fstab.fs_vfstype):
                    fstab_nfs_mounts.append(" - {} {}\n".format(fstab.fs_spec, fstab.fs_file))

            # Check mount
            nfs_mounts = []
            for mount in storage.mount:
                if _is_nfs(mount.tp):
                    nfs_mounts.append(" - {} {}\n".format(mount.name, mount.mount))

            # Check systemd-mount
            systemd_nfs_mounts = []
            for systemdmount in storage.systemdmount:
                if _is_nfs(systemdmount.fs_type):
                    # mountpoint is not available in the model
                    systemd_nfs_mounts.append(" - {}\n".format(systemdmount.node))

        if any((fstab_nfs_mounts, nfs_mounts, systemd_nfs_mounts)):
            if fstab_nfs_mounts:
                details += "- NFS shares found in /etc/fstab:\n"
                details += ''.join(fstab_nfs_mounts)

            if nfs_mounts:
                details += "- NFS shares currently mounted:\n"
                details += ''.join(nfs_mounts)

            if systemd_nfs_mounts:
                details += "- NFS mounts configured with systemd-mount:\n"
                details += ''.join(systemd_nfs_mounts)

            fstab_related_resource = [reporting.RelatedResource('file', '/etc/fstab')] if fstab_nfs_mounts else []

            create_report([
                reporting.Title("Use of NFS detected. Upgrade can't proceed"),
                reporting.Summary(details),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([
                        reporting.Groups.FILESYSTEM,
                        reporting.Groups.NETWORK
                ]),
                reporting.Remediation(hint='Disable NFS temporarily for the upgrade if possible.'),
                reporting.Groups([reporting.Groups.INHIBITOR]),
                ] + fstab_related_resource
            )
