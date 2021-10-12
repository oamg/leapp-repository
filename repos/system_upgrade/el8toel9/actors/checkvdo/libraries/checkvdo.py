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
        raise exceptions.StopActorExecutionError('Failure to execute "{0}"'.format(' '.join(command)))
    return result

def _canonicalize_device_path(path):
    return os.path.realpath(path)

#
# Methods used in discovering VDO devices which require migration to
# lvm-based management.
#
def _get_unmigrated_vdo_blkid_results():
    """ Collect devices that have not been migrated to lvm-based management. """
    # VDO devices that have been migrated to lvm-based management are
    # not identified by blkid.
    command = ['blkid', '--output', 'device', '--match-token', 'TYPE=vdo']
    result = _run_cmd(command, checked = False)
    exit_code = result['exit_code']
    if (exit_code != 0) and (exit_code != 2):
        raise exceptions.StopActorExecutionError('blkid exited with code: {0}'.format(exit_code))
    return '' if exit_code != 0 else result['stdout']


def _get_unmigrated_vdo_devices():
    results = _get_unmigrated_vdo_blkid_results()
    # Canonicalize the device paths.
    return [_canonicalize_device_path(x) for x in results.splitlines()]


#
# Methods used in discovering VDO devices for which migration to lvm-based
# management was attempted but not completed.
#
def _get_migration_failed_blkid_results():
    """ Collect all devices blkid identifies. """
    command = ['blkid', '--output', 'device']
    return _run_cmd(command)['stdout']


def _get_migration_failed_canonical_blkid_results():
    """ Collect canonical devices blkid identifies. """
    results = _get_migration_failed_blkid_results()
    # Canonicalize the device paths.
    return [_canonicalize_device_path(x) for x in results.splitlines()]


def _get_migration_failed_lsblk_results():
    """ Collect all devices known to the system. """
    command = ['lsblk', '--noheadings', '--output', 'NAME,TYPE', '--path', '--list']
    return _run_cmd(command)['stdout']


def _get_migration_failed_lsblk_info():
    """ Collect canonical devices lsblk identifies. """
    results = _get_migration_failed_lsblk_results()
    info = {}
    for line in results.splitlines():
        # Use 'kind' for type as 'type' is a python entity.
        (device, kind) = line.split()
        device = _canonicalize_device_path(device)
        info[device] = { "type" : kind }
    return info


def _get_migration_failed_pvs_results():
    """ Collect all devices configued as physical volumes. """
    command = ['pvs', '--noheadings', '--options', 'pv_name,vg_name']
    return _run_cmd(command)['stdout']


def _get_migration_failed_pvs_info():
    """ Collect canonical devices pvs identifies. """
    results = _get_migration_failed_pvs_results()
    info = {}
    for line in results.splitlines():
        # We can't just do tuple assignment as if the physical volume is
        # not part of a volume group the line split will not contain the
        # requisite items.
        line_list = line.split()
        device = line_list[0]
        vg = None if len(line_list) < 2 else line_list[1]
        device = _canonicalize_device_path(device)
        info[device] = { "vg" : vg }
    return info


def _is_post_migration_vdo_device(device):
    # TODO: Invoke the utility (when it exists) to check the device as being a
    #       post-migration vdo
    # XXX:  Do lvm-created vdos identify as post-migration vdos?  If so we'll
    #       need another approach to identify and remove them.
    return True


def _get_post_migration_vdo_devices():
    """ Collect all vdo devices that have been migrated for lvm-based management. """
    lsblk_info = _get_migration_failed_lsblk_info()

    # Exclude ROM and VDO devices.
    # Any vdo devices appearing here are unmigrated; we could leave them in
    # and rely on the post-migration device check, but there's no reason to
    # do so.
    devices = set([device for (device, info) in lsblk_info.items()
                          if info['type'] not in ['rom', 'vdo']])

    # VDO devices that have been migrated to lvm-based management are not
    # identified by blkid.
    # Remove any devices that blkid can identify.
    devices -= set(_get_migration_failed_canonical_blkid_results())

    return [x for x in devices if _is_post_migration_vdo_device(x)]


def _get_migration_failed_vdo_devices():
    post_migration_devices = _get_post_migration_vdo_devices()

    # Exclude physical volumes that are part of a volume group.
    pv_info = _get_migration_failed_pvs_info()
    pvs = set([device for (device, info) in pv_info.items()
                      if info['vg'] is not None])

    post_migration_devices = list(set(post_migration_devices) - set(pvs))

    # The remaining devices are those that got migrated at the vdo-level
    # but did not make it (for whatever reason) into lvm-based management.
    return post_migration_devices


# Check for vdo devices that must be migrated to lvm management.
def _check_for_unmigrated_vdo_devices():
    # Find VDO devices that have not been migrated to lvm-based management.
    unmigrated_vdo_devices = _get_unmigrated_vdo_devices()

    if len(unmigrated_vdo_devices) == 0:
        # Generate report indicating there are no vdo devices to migrate.
        reporting.create_report([
            reporting.Title('VDO devices migration to lvm-based management'),
            reporting.Summary('VDO devices that require migration: None'),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS])
        ])
    else:
        devices = [device for device in unmigrated_vdo_devices]
        reporting.create_report([
            reporting.Title('VDO devices migration to lvm-based management'),
            reporting.Summary('VDO devices that require migration: {0}'.format(', '.join(devices))),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
            reporting.Remediation(hint = 'Perform VDO to LVM migration on the VDO devices.'),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])


def _check_for_migration_failed_vdo_devices():
    # Find VDO devices that did not complete migration to lvm-based management.
    # This could result from system failures during the migration process.
    migration_failed_vdo_devices = _get_migration_failed_vdo_devices()
    if len(migration_failed_vdo_devices) > 0:
        devices = [device for device in migration_failed_vdo_devices]
        reporting.create_report([
            reporting.Title('VDO devices migration to lvm-based management'),
            reporting.Summary('VDO devices that did not complete migration: {0}'.format(', '.join(devices))),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
            reporting.Remediation(hint = 'Complete VDO to LVM migration for the VDO devices.'),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])


def check_vdo():
    _check_for_unmigrated_vdo_devices()
    _check_for_migration_failed_vdo_devices()
