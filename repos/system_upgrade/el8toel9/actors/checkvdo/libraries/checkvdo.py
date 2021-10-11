import os

from leapp import exceptions
from leapp import models
from leapp import reporting
from leapp.libraries import stdlib

def _run_cmd(command, checked = True):
    """ Run the specified command returning the result. """
    try:
        result = stdlib.run(command, checked = checked)
    except stdlib.CalledProcessError:
        raise exceptions.StopActorExecutionError('Failure to execute "{0}"'.format(" ".join(command)))
    return result

def _canonicalize_device_path(path):
    return os.path.realpath(path)

#
# Methods used in discovering VDO instances which require migration to
# lvm-based management.
#
def _get_blkid_vdo_results():
    """ Collect devices that have not been migrated to lvm-based management. """
    # VDO instances that have been migrated to lvm-based management are
    # not identified by blkid as vdo type.
    command = ['blkid', '--output', 'device', '--match-token', 'TYPE=vdo']
    result = _run_cmd(command, checked = False)
    exit_code = result['exit_code']
    if (exit_code != 0) and (exit_code != 2):
        raise exceptions.StopActorExecutionError('blkid exited with code: {0}'.format(exit_code))
    return "" if exit_code != 0 else result['stdout']


def _get_unmigrated_vdo_devices():
    results = _get_blkid_vdo_results()
    # Canonicalize the device paths.
    return [_canonicalize_device_path(x.strip()) for x in results.splitlines()]


def _get_dmsetup_vdo_results():
    command = ['dmsetup', 'status', '--target', 'vdo']
    return _run_cmd(command)['stdout']


def _get_unmigrated_vdo_devices_info():
    """ Return info for the specified devices. """
    devices = _get_unmigrated_vdo_devices()
    results = _get_dmsetup_vdo_results()
    info = {}
    for line in results.splitlines():
        (name, _, _, _, device, *_) = line.split()
        # Canonicalize the device path.
        device = _canonicalize_device_path(device)
        info[device] = name.rstrip(':')
    for device in (set(devices) - set(info.keys())):
        info[device] = "<unknown-name>"
    return info


# Check for vdo instances that must be migrated to lvm management.
def check_vdo():
    # Find VDO devices that have not been migrated to lvm-based management.
    unmigrated_vdo_devices = _get_unmigrated_vdo_devices_info()

    if len(unmigrated_vdo_devices) == 0:
        # Generate report indicating there are no vdo instances to migrate.
        reporting.create_report([
            reporting.Title('VDO instances migration to lvm-based management'),
            reporting.Summary('VDO instances that require migration: None'),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS])
        ])
    else:
        instances = ['{0}[{1}]'.format(name, device)
                      for (device, name) in unmigrated_vdo_devices.items()]
        reporting.create_report([
            reporting.Title('VDO instances migration to lvm-based management'),
            reporting.Summary('VDO instances that require migration: {0}'.format(', '.join(instances))),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
            reporting.Remediation(hint = 'Perform VDO to LVM migration on the VDO instances.'),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])

    # TDOO: Find vdo instances that were in the process of being migrated
    #       to lvm-based management but didn't complete the process.
