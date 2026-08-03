from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import is_conversion
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts


def _report_secureboot_enabled(extra_hint=''):
    hint = (
        "Disable Secure Boot to be able to convert the system to"
        " a different Linux distribution. Then re-enable Secure Boot"
        " again after the conversion process is finished successfully."
        " Check instructions for your current OS, or hypervisor in"
        " case of virtual machines, for more information how to"
        " disable Secure Boot."
    )
    if extra_hint:
        hint += ' ' + extra_hint
    reporting.create_report([
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
        reporting.Remediation(hint=hint),
    ])


def process():
    if not is_conversion():
        return

    ff = next(api.consume(FirmwareFacts), None)
    if not ff:
        raise StopActorExecutionError(
            "Could not identify system firmware",
            details={"details": "Actor did not receive FirmwareFacts message."},
        )

    if ff.firmware != 'efi':
        return

    secureboot_enabled = ff.secureboot_enabled

    # Hardware does not support Secure Boot (EFI vars readable, state is None).
    if secureboot_enabled is None and ff.efi_vars_accessible is True:
        api.current_logger().info(
            "EFI variables are accessible but Secure Boot is not supported"
            " by the hardware; proceeding."
        )
        return

    # EFI runtime variables inaccessible -> the user's answer is our only source.
    answered_by_user = False
    if secureboot_enabled is None:
        secureboot_enabled = api.current_actor().get_sb_answer()
        answered_by_user = True

    if secureboot_enabled is True:
        _report_secureboot_enabled(
            extra_hint=(
                "If Secure Boot is already disabled and the answer was"
                " incorrect, change the value of 'confirm_secureboot_enabled'"
                " from True to False in the answer file and re-run."
            ) if answered_by_user else '',
        )
        return

    if secureboot_enabled is False:
        if answered_by_user:
            api.current_logger().info(
                "User confirmed Secure Boot is disabled; proceeding despite"
                " inaccessible EFI variables."
            )
        return

    # Still None -> user did not answer; state genuinely undeterminable.
    reporting.create_report([
        reporting.Title("Cannot determine the Secure Boot status"),
        reporting.Summary(
            "The system is booted in UEFI mode but the Secure Boot state"
            " cannot be determined automatically because EFI runtime"
            " variables are not accessible. The Secure Boot status is"
            " important for the conversion process as converting with"
            " Secure Boot enabled could lead to a system that fails"
            " to boot."
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.BOOT]),
        reporting.Remediation(
            hint="Verify the Secure Boot status in your UEFI firmware"
            " settings. If Secure Boot is enabled, disable it before"
            " proceeding with the conversion. Then provide the Secure Boot"
            " status by setting the value of 'confirm_secureboot_enabled'"
            " to True or False in the answer file and re-run."
        ),
    ])
