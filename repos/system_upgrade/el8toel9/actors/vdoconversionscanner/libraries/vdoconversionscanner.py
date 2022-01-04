import os

from leapp import models, reporting
from leapp.libraries import stdlib
from leapp.libraries.common import rpms


_report_title = reporting.Title('VDO devices migration to lvm-based management')


def _run_cmd(command, checked = True):
    """ Run the specified command returning the result. """
    return stdlib.run(command, checked = checked)


def _command_failure_report(command, exit_code):
    reporting.create_report([
        _report_title,
        reporting.Summary('"{0}" required for successful opeation failed; exit_code: {1}'.format(' '.join(command),
                                                                                                 exit_code)),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
        reporting.Flags([reporting.Flags.INHIBITOR])
    ])


def _is_vdo_lvm_managed(device):
    """
    Determines if the specified device (which has already been identified
    as a post-conversion vdo device (at the level of vdo) is managed by lvm.

    If an unexpected exit code is returned from blkid an inhibitory report will
    be generated and the return value will indicate the device is not lvm
    managed.
    """
    command = ['blkid', '--match-token', 'TYPE=LVM2_member', device]
    result = _run_cmd(command, checked = False)
    exit_code = result['exit_code']
    if exit_code not in (0, 2):
        _command_failure_report(command, exit_code)
    return exit_code == 0


def _get_vdo_pre_conversion(device):
    """
    Identify if the specified device is either not a vdo device, a
    pre-conversion vdo device or a post-conversion vdo device.

    If an unexpected exit code is returned from the conversion utility an
    inhibitory report will be generated and the return value from this
    method will indicate the device is not a vdo device and therefore requires
    no further processing.
    """
    conversion_utility = os.path.join(os.getenv('VDO_CONVERSION_UTILITY_DIR',
                                                '/usr/libexec'),
                                      'vdoprepareforlvm')
    command = [conversion_utility, '--check', device]
    result = _run_cmd(command, checked = False)
    exit_code = result['exit_code']
    # 255: Not a vdo device
    #   0: A post-conversion vdo device
    #   1: A pre-conversion vdo device
    if exit_code not in (255, 0, 1):
        _command_failure_report(command, exit_code)
        exit_code = 255
    return exit_code


def _required_packages_not_installed():
    not_installed = []
    if not rpms.has_package(models.InstalledRedHatSignedRPM, 'vdo'):
        not_installed.append('vdo')
    return not_installed


def _get_vdos(storage_info):
    pre_conversion_vdos = []
    post_conversion_vdos = []

    for lsblk in storage_info.lsblk:
        if lsblk.tp not in ('disk', 'part'):
            continue

        device = '/dev/{0}'.format(lsblk.name)
        pre_conversion = _get_vdo_pre_conversion(device)
        if pre_conversion == 255:
            # Not a vdo.
            continue

        if pre_conversion:
            pre_conversion_vdos.append(
              models.VdoPreConversion(name = lsblk.name))
        else:
            post_conversion_vdos.append(
              models.VdoPostConversion(name = lsblk.name,
                                       complete = _is_vdo_lvm_managed(device)))

    return (pre_conversion_vdos, post_conversion_vdos)


def get_info(storage_info):
    pre_conversion_vdos = []
    post_conversion_vdos = []

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
        (pre_conversion_vdos, post_conversion_vdos) = _get_vdos(storage_info)


    return models.VdoConversionInfo(pre_conversion_vdos = pre_conversion_vdos,
                                    post_conversion_vdos = post_conversion_vdos)
