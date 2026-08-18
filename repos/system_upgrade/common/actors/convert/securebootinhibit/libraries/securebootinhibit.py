from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import is_conversion
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts


def _report_secureboot_enabled(answered_by_user):
    answerfile_hint = ''
    if answered_by_user:
        # extra space in the beginning due to pasting inside the hint str
        answerfile_hint = (
            ' '
            'Then update your answer about the secure boot state in the answerfile'
            ' to reflect the new state (for key: "confirm_secureboot_enabled").'
        )

    hint = (
        'To be able to convert the system to a different Linux distribution,'
        ' disable Secure Boot.{} Then re-enable Secure Boot'
        ' again after the upgrade and conversion process is finished successfully.'
        ' Check instructions for your current OS, or hypervisor in'
        ' case of virtual machines, for more information how to'
        ' disable Secure Boot.'
        .format(answerfile_hint)
    )

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
        reporting.Remediation(hint=hint),
    ])


def _report_missing_answer():
    reporting.create_report([
        reporting.Title('Cannot determine the Secure Boot state'),
        reporting.Summary(
            'The system is booted in UEFI mode but the Secure Boot state'
            ' cannot be determined automatically because EFI runtime'
            ' variables are not accessible. The information Secure Boot state'
            ' is required to determine the next steps for the in-place upgrade'
            ' and conversion process.'
        ),

        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.BOOT]),
        reporting.Remediation(
            hint='Verify the Secure Boot state in your UEFI firmware'
            ' settings. If Secure Boot is enabled, disable it before'
            ' proceeding with the upgrade and conversion. Then provide the Secure Boot'
            ' state by setting the value of "confirm_secureboot_enabled"'
            ' to True or False in the answer file and re-run.'
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

    if ff.firmware != 'efi' or ff.secureboot_enabled is False:
        return

    secureboot_enabled = ff.secureboot_enabled
    if secureboot_enabled is None and ff.efi_vars_accessible is True:
        # HW does not support Secure Boot (EFI vars readable, SB state is None).
        api.current_logger().info('Secure Boot is not supported by the HW. Skipping.')
        return

    answered_by_user = False
    if secureboot_enabled is None:
        # Cannot determine the SB state (no EFI vars) -> get answer from user
        secureboot_enabled = api.current_actor().get_sb_answer()
        if secureboot_enabled is None:
            _report_missing_answer()
            return
        answered_by_user = True

    if secureboot_enabled is True:
        _report_secureboot_enabled(answered_by_user)
    else:
        api.current_logger().info(
            'User confirmed Secure Boot is disabled; proceeding despite'
            ' inaccessible EFI variables.'
        )
