import re

from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import MachineIdInfo

_VALID_MACHINE_ID_RE = re.compile(r'^[0-9a-f]{32}$')
_ALL_ZEROS = '0' * 32


def process():
    machine_id_info = next(api.consume(MachineIdInfo), None)
    if not machine_id_info:
        api.current_logger().warning(
            'The MachineIdInfo message is missing. Skipping the check of /etc/machine-id.'
        )
        return

    if (machine_id_info.machine_id
            and _VALID_MACHINE_ID_RE.match(machine_id_info.machine_id)
            and machine_id_info.machine_id != _ALL_ZEROS):
        return

    reporting.create_report([
        reporting.Title('Missing or invalid /etc/machine-id file'),
        reporting.Summary(
            'The /etc/machine-id file is missing or does not contain a valid'
            ' machine ID. A valid machine ID is a 32-character lowercase'
            ' hexadecimal string that is not all zeros. Various system'
            ' components rely on a valid machine ID and the upgrade cannot'
            ' proceed without one.'
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SANITY, reporting.Groups.INHIBITOR]),
        reporting.Remediation(
            hint=(
                'Generate a valid machine ID by running `systemd-machine-id-setup`.'
                ' See `man machine-id` and `man systemd-machine-id-setup` for details.'
            )
        ),
        reporting.ExternalLink(
            url='https://access.redhat.com/solutions/3600401',
            title='How to reconfigure the machine-id?'
        ),
        reporting.RelatedResource('file', '/etc/machine-id'),
    ])
