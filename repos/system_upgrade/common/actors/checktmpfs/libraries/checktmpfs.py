from leapp import reporting
from leapp.reporting import create_report


def checktmpfs(storage_info):
    for storage in storage_info:
        if any(entry.fs_file == "/tmp" for entry in storage.fstab):
            create_report(
                [
                    reporting.Title("/tmp entry detected in /etc/fstab"),
                    reporting.Summary(
                        "The upgrade environment may fail to mount /tmp if it is defined "
                        "in /etc/fstab, particularly if it conflicts with the upgrade "
                        'RAM disk. This is known to cause "failed with exit code 32" errors.'
                    ),
                    reporting.Key("fstab_non_tmpfs_tmp_detected"),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups(
                        [
                            reporting.Groups.FILESYSTEM,
                            reporting.Groups.INHIBITOR,
                        ]
                    ),
                    reporting.Remediation(
                        hint="Comment out the /tmp entry from /etc/fstab to proceed with the upgrade."
                    ),
                    reporting.RelatedResource("file", "/etc/fstab"),
                ]
            )
