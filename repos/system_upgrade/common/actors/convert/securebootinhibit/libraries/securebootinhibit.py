from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import is_conversion
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts


def _resolve_unknown_sb_state(ff):
    if ff.efi_vars_accessible is True:
        api.current_logger().info(
            'EFI variables are accessible but Secure Boot is not supported'
            ' by the hardware; proceeding.'
        )
        return

    sb_answer = api.current_actor().get_sb_answer()

    if sb_answer is False:
        api.current_logger().info(
            'User confirmed Secure Boot is disabled; proceeding despite'
            ' inaccessible EFI variables.'
        )
        return

    if sb_answer is True:
        reporting.create_report([
            reporting.Title(
                'Detected enabled Secure Boot when trying to convert the system'
            ),
            reporting.Summary(
                'The user confirmed that Secure Boot is enabled on this system.'
                ' Conversion to a different Linux distribution is not possible'
                ' when the Secure Boot is enabled. Artifacts of the target'
                ' Linux distribution are signed by keys that are not accepted'
                ' by the source Linux distribution.'
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.BOOT]),
            reporting.Remediation(
                hint='Disable Secure Boot in your UEFI firmware settings'
                ' before proceeding with the conversion.'
            ),
        ])
        return

    reporting.create_report([
        reporting.Title('EFI runtime variables are not accessible'),
        reporting.Summary(
            'The system is booted in UEFI mode but EFI runtime variables'
            ' are not accessible. The Secure Boot state cannot be'
            ' determined automatically.'
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.BOOT]),
        reporting.Remediation(
            hint='Verify the Secure Boot status in your UEFI firmware settings.'
            ' If Secure Boot is enabled, disable it before proceeding'
            ' with the conversion. Converting with Secure Boot enabled while'
            ' EFI variables are inaccessible may result in an unbootable'
            ' system.'
        ),
    ])


def process():
    if not is_conversion():
        return

    ff = next(api.consume(FirmwareFacts), None)
    if not ff:
        raise StopActorExecutionError(
            'Could not identify system firmware',
            details={'details': 'Actor did not receive FirmwareFacts message.'},
        )

    if ff.firmware != 'efi':
        return

    if ff.secureboot_enabled is True:
        reporting.create_report([
            reporting.Title(
                'Detected enabled Secure Boot when trying to convert the system'
            ),
            reporting.Summary(
                'Conversion to a different Linux distribution is not possible'
                ' when the Secure Boot is enabled. Artifacts of the target'
                ' Linux distribution are signed by keys that are not accepted'
                ' by the source Linux distribution.'
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.BOOT]),
            reporting.Remediation(
                hint='Disable Secure Boot to be able to convert the system to'
                ' a different Linux distribution. Then re-enable Secure Boot'
                ' again after the conversion process is finished successfully.'
                ' Check instructions for your current OS, or hypervisor in'
                ' case of virtual machines, for more information how to'
                ' disable Secure Boot.'
            ),
        ])
        return

    if ff.secureboot_enabled is False:
        return

    _resolve_unknown_sb_state(ff)
