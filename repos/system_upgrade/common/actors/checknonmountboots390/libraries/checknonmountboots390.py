import os

from leapp import reporting
from leapp.libraries.common.config import architecture


def perform_check():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        return

    if os.path.ismount('/boot'):
        return

    data = [
        reporting.Title('Leapp detected known issue related to /boot on s390x architecture'),
        reporting.Summary((
            'Due to a bug in the Leapp code, there is a situation when the upgrade process'
            ' removes content of /boot when the directory is not on a separate partition and'
            ' the system is running on S390x architecture. To avoid this from happening, we'
            ' are inhibiting the upgrade process in this release until the issue has been fixed.'
        )),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Groups([reporting.Groups.FILESYSTEM, reporting.Groups.UPGRADE_PROCESS, reporting.Groups.BOOT]),
        reporting.Severity(reporting.Severity.HIGH),
    ]

    reporting.create_report(data)
