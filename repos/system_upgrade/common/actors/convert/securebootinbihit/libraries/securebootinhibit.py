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
            'Could not identify system firmware',
            details={'details': 'Actor did not receive FirmwareFacts message.'}
        )

    if ff.firmware == 'efi' and ff.secureboot_enabled:
        reporting.create_report([
            reporting.Title('SecureBoot is enabled'),
            reporting.Summary((
                'Upgrades with conversions are currently not possible when SecureBoot'
                ' is enabled in the UEFI.'
            )),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.BOOT]),
            # TODO some link
            reporting.Remediation(hint='Peform the upgrade with SecureBoot disabled.'),
        ])
