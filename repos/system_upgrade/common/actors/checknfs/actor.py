from leapp import reporting
from leapp.actors import Actor
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
        details = "NFS is currently not supported by the inplace upgrade.\n" \
                  "We have found NFS usage at the following locations:\n"
        nfs_found = False

        def _is_nfs(a_type):
            return a_type.startswith('nfs') and a_type != 'nfsd'

        for storage in self.consume(StorageInfo):
            # Check fstab
            for fstab in storage.fstab:
                if _is_nfs(fstab.fs_vfstype):
                    nfs_found = True
                    details += "- One or more NFS entries in /etc/fstab\n"
                    break

            # Check mount
            for mount in storage.mount:
                if _is_nfs(mount.tp):
                    nfs_found = True
                    details += "- Currently mounted NFS share:\n"
                    details += "%s %s %s %s\n" % (mount.name, mount.mount, mount.tp, mount.options)
                    break

            # Check systemd-mount
            for systemdmount in storage.systemdmount:
                if _is_nfs(systemdmount.fs_type):
                    nfs_found = True
                    details += "- One or more configured NFS mounts in systemd-mount\n"
                    break

        if nfs_found:
            create_report([
                reporting.Title("Use of NFS detected. Upgrade can't proceed"),
                reporting.Summary(details),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Tags([
                        reporting.Tags.FILESYSTEM,
                        reporting.Tags.NETWORK
                ]),
                reporting.Remediation(hint='Disable NFS temporarily for the upgrade if possible.'),
                reporting.Flags([reporting.Flags.INHIBITOR]),
                reporting.RelatedResource('file', '/etc/fstab')
            ])
