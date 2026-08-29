import glob
import os
from typing import List, Optional

from leapp import reporting
from leapp.libraries.common.config import is_conversion
from leapp.libraries.stdlib import api, format_list
from leapp.models import MachineIdInfo

MACHINE_ID_PATH = '/etc/machine-id'
BOOT_ENTRIES_PATH = '/boot/loader/entries'


def _read_machine_id() -> Optional[str]:
    try:
        with open(MACHINE_ID_PATH, 'r') as f:
            return f.read().strip()
    except OSError as e:
        api.current_logger().warning('Failed to read {}: {}'.format(MACHINE_ID_PATH, e))
        return None


def _remove_stale_entries(machine_id: str) -> List[str]:
    """
    Remove boot loader entries whose file name doesn't contain the machine ID.

    Return the list of removed entry paths.
    """
    removed = []
    for entry in glob.glob(os.path.join(BOOT_ENTRIES_PATH, '*.conf')):
        if machine_id in os.path.basename(entry):
            continue
        try:
            os.remove(entry)
            removed.append(entry)
            api.current_logger().info('Removed stale boot loader entry {}'.format(entry))
        except OSError as e:
            api.current_logger().warning('Failed to remove boot loader entry {}: {}'.format(entry, e))
    return removed


def process() -> None:
    if not is_conversion():
        return

    machine_id = _read_machine_id()
    if not machine_id:
        api.current_logger().warning(
            'Could not determine the current machine ID, skipping boot loader entry cleanup.'
        )
        return

    original = next(api.consume(MachineIdInfo), None)
    if original and original.machine_id and original.machine_id != machine_id:
        api.current_logger().info(
            'The machine ID changed during the upgrade (before: {}, after: {}).'.format(
                original.machine_id, machine_id
            )
        )

    removed = _remove_stale_entries(machine_id)
    if not removed:
        return

    reporting.create_report([
        reporting.Title('Removed obsolete boot loader entries'),
        reporting.Summary(
            'The following boot loader entries in {} did not match'
            ' the current machine ID ({}) and have been removed:{}'.format(
                BOOT_ENTRIES_PATH, machine_id, format_list(removed)
            )
        ),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.BOOT, reporting.Groups.POST]),
    ])
