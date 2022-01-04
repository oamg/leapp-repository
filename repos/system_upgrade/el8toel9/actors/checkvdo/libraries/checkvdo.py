import os

from leapp import exceptions, models, reporting
from leapp.libraries import stdlib
from leapp.libraries.common import rpms

_report_title = reporting.Title('VDO devices migration to lvm-based management')

def _run_cmd(command, checked = True):
    """ Run the specified command returning the result. """
    return stdlib.run(command, checked = checked)


def _canonicalize_device_path(path):
    return os.path.realpath(path)


def _command_failure_report(command, exit_code):
    reporting.create_report([
        _report_title,
        reporting.Summary('"{0}" required for successful opeation failed; exit_code: {1}'.format(' '.join(command),
                                                                                                 exit_code)),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
        reporting.Flags([reporting.Flags.INHIBITOR])
    ])


#
# Methods used in discovering VDO devices which require migration to
# lvm-based management.
#
def _get_unmigrated_vdo_blkid_results():
    """ Collect devices that have not been migrated to lvm-based management. """
    # VDO devices that have been created by or migrated to lvm-based management
    # are not identified by blkid.
    command = ['blkid', '--output', 'device', '--match-token', 'TYPE=vdo']
    result = _run_cmd(command, checked = False)
    exit_code = result['exit_code']
    if exit_code not in (0, 2):
        _command_failure_report(command, exit_code)
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
    # VDO devices that have been created by or migrated to lvm-based management
    # are not identified by blkid.
    command = ['blkid', '--output', 'device']
    return _run_cmd(command)['stdout']


def _get_migration_failed_canonical_blkid_results():
    """ Collect canonical devices blkid identifies. """
    results = _get_migration_failed_blkid_results()
    # Canonicalize the device paths.
    return [_canonicalize_device_path(x) for x in results.splitlines()]


def _get_migration_failed_lsblk_results():
    """ Collect all devices known to the system. """
    # lsblk does not identify lvm-managed vdos as vdos.
    # Any such devices will be eliminated by the check for being a
    # post-migration vdo as the check will identify them as pre-migration vdos.
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
        info[device] = {"type": kind}
    return info


def _is_post_migration_vdo_device(device):
    """ Identify if the specified device is a post-migration vdo device. """
    # A post-migration vdo device is a vdo device which has completed its
    # preparation for being managed by lvm but for which lvm has failed (for
    # whatever reason; e.g., system crash) to take up that responsibility.
    #
    # N.B. lvm-managed vdos will make it to the point of being checked here.
    #      This is due to the fact that they are not recognized by either
    #      blkid or lsblk as vdo devices and are thus not eliminated using the
    #      results of those.
    #      They are, though, recognized by the conversion utility as
    #      pre-migration vdo devices and are thus eliminated by this check.
    conversion_utility = os.path.join(os.getenv('VDO_CONVERSION_UTILITY_DIR',
                                                '/usr/libexec'),
                                      'vdoprepareforlvm')
    command = [conversion_utility, '--check', device]
    result = _run_cmd(command, checked = False)
    exit_code = result['exit_code']
    # 255: Not a vdo device
    #   0: A post-migration vdo device
    #   1: A pre-migration vdo device
    if exit_code not in (255, 0, 1):
        _command_failure_report(command, exit_code)
    return exit_code == 0


def _get_migration_failed_vdo_devices():
    """ Collect all vdo devices that have been migrated for lvm-based management. """
    lsblk_info = _get_migration_failed_lsblk_info()

    # Exclude ROM and VDO devices.
    # Any vdo devices appearing here are unmigrated (lsblk does not identify
    # lvm-managed vdos as vdos); we could leave them in and rely on the
    # post-migration device check, but there's no reason to do so.
    devices = set([device for (device, info) in lsblk_info.items()
                          if info['type'] not in ['rom', 'vdo']])

    # VDO devices that have been created by or migrated to lvm-based management
    # are not identified by blkid.
    # Remove any devices that blkid can identify.
    devices -= set(_get_migration_failed_canonical_blkid_results())

    return [x for x in devices if _is_post_migration_vdo_device(x)]


# Check for vdo devices that must be migrated to lvm management.
def _check_for_unmigrated_vdo_devices():
    # Find VDO devices that have not been migrated to lvm-based management.
    unmigrated_vdo_devices = _get_unmigrated_vdo_devices()

    if unmigrated_vdo_devices:
        reporting.create_report([
            _report_title,
            reporting.Summary('VDO devices that require migration: {0}'.format(', '.join(unmigrated_vdo_devices))),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
            reporting.Remediation(hint = 'Perform VDO to LVM migration on the VDO devices.'),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])
    else:
        # Generate report indicating there are no vdo devices to migrate.
        reporting.create_report([
            _report_title,
            reporting.Summary('VDO devices that require migration: None'),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS])
        ])


def _check_for_migration_failed_vdo_devices():
    # Find VDO devices that did not complete migration to lvm-based management.
    # This could result from system failures during the migration process.
    migration_failed_vdo_devices = _get_migration_failed_vdo_devices()
    if migration_failed_vdo_devices:
        reporting.create_report([
            _report_title,
            reporting.Summary('VDO devices that did not complete migration: {0}'.format(
                                ', '.join(migration_failed_vdo_devices))),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
            reporting.Remediation(hint = 'Complete VDO to LVM migration for the VDO devices.'),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])


def _required_packages_not_installed():
    not_installed = []
    if not rpms.has_package(models.InstalledRedHatSignedRPM, 'vdo'):
        not_installed.append('vdo')
    return not_installed


def check_vdo():
    packages_not_installed = _required_packages_not_installed()
    if packages_not_installed:
        reporting.create_report([
            _report_title,
            reporting.Summary('"{0}" package(s) required for upgrade validation check'.format(
                                ', '.join(packages_not_installed))),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
            reporting.Remediation(hint = 'Install required package(s).'),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])
    else:
        _check_for_unmigrated_vdo_devices()
        _check_for_migration_failed_vdo_devices()
