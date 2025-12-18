from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import is_conversion
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts


def process():
    if not is_conversion():
        return

    ff = next(api.consume(FirmwareFacts), None)
    if not ff:
        raise StopActorExecutionError(
            "Could not identify system firmware",
            details={"details": "Actor did not receive FirmwareFacts message."},
        )

    if ff.firmware == "efi" and ff.secureboot_enabled:
        report = [
            reporting.Title(
                "Detected enabled Secure Boot when trying to convert the system"
            ),
            reporting.Summary(
                "Conversion to a different Linux distribution is not possible"
                " when the Secure Boot is enabled. Artifacts of the target"
                " Linux distribution are signed by keys that are not accepted"
                " by the source Linux distribution."
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.BOOT]),
            # TODO some link
            reporting.Remediation(
                hint="Disable Secure Boot to be able to convert the system to"
                " a different Linux distribution. Then re-enable Secure Boot"
                " again after the upgrade process is finished successfully."
                " Check instructions for your current OS, or hypervisor in"
                " case of virtual machines, for more information how to"
                " disable Secure Boot."
            ),
        ]
        reporting.create_report(report)
