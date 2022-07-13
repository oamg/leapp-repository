import os

from leapp import models
from leapp.libraries.common import rpms
from leapp.libraries.stdlib import api, run

MIN_DISK_SIZE = 2 ** 22  # 4 MiB


def _check_vdo_lvm_managed(device):
    """
    Determines if the specified device (which has already been identified
    as a post-conversion vdo device (at the level of vdo) is managed by lvm.
    """
    command = ['blkid', '--match-token', 'TYPE=LVM2_member', device]
    result = run(command, checked=False)
    exit_code = result['exit_code']
    #     0: Is LVM managed
    #     2: Is not LVM manaaged
    # other: Unexpected
    return exit_code


def _check_vdo_pre_conversion(device):
    """
    Identify if the specified device is either not a vdo device, a
    pre-conversion vdo device or a post-conversion vdo device.
    """
    command = ['/usr/libexec/vdoprepareforlvm', '--check', device]
    result = run(command, checked=False)
    exit_code = result['exit_code']
    #   255: Not a vdo device
    #     0: A post-conversion vdo device
    #     1: A pre-conversion vdo device
    # other: Unexpected
    return exit_code


def _lvm_package_installed():
    return rpms.has_package(models.InstalledRedHatSignedRPM, 'lvm2')


def _vdo_package_installed():
    return rpms.has_package(models.InstalledRedHatSignedRPM, 'vdo')


def get_info(storage_info):
    pre_conversion_devices = []
    post_conversion_devices = []
    undetermined_conversion_devices = []

    # Only if lvm is installed can there be VDO instances.
    if _lvm_package_installed():
        vdo_package_installed = _vdo_package_installed()

        for lsblk in storage_info.lsblk:
            # NOTE: partitions < MIN_DISK_SIZE cannot be handled by vdo and
            # the check results in unexpected outputs
            if lsblk.tp not in ('disk', 'part') or lsblk.bsize < MIN_DISK_SIZE:
                continue

            if not vdo_package_installed:
                undetermined_conversion_devices.append(
                    models.VdoConversionUndeterminedDevice(name=lsblk.name))
                continue

            # refer to kernel name
            device = '/dev/{0}'.format(lsblk.kname)
            if not os.path.exists(device):
                # NOTE: Corner case. It's hypothetical situation which could possibly
                # happen but we do not know under what circumstances and we do not
                # have time now for investigation. Let's see if someone report it
                # to us so we will have a data :)
                # For now, stay on the safe side and inhibit the upgrade if this
                # happens.
                failure = (
                    'cannot check device {0} (kernel name: {1}): file {2} does not exist'
                    .format(lsblk.name, lsblk.kname, device)
                )
                api.current_logger().warning(failure)
                undetermined_conversion_devices.append(
                    models.VdoConversionUndeterminedDevice(
                        name=lsblk.name,
                        check_failed=True,
                        failure=failure
                    )
                )
                continue
            result = _check_vdo_pre_conversion(device)
            if result not in (255, 0, 1):
                failure = (
                    'unexpected error from \'vdoprepareforlvm\' for {0}; result = {1}'
                    .format(lsblk.name, result)
                )
                undetermined_conversion_devices.append(
                    models.VdoConversionUndeterminedDevice(
                        name=lsblk.name,
                        check_failed=True,
                        failure=failure
                    )
                )
                continue

            if result == 255:
                # Not a vdo.
                continue

            if result:
                pre_conversion_devices.append(
                  models.VdoConversionPreDevice(name=lsblk.name))
            else:
                result = _check_vdo_lvm_managed(device)
                failure = (None if result in (0, 2) else
                           'unexpected error from \'blkid\' for {0}; '
                           'result = {1}'.format(lsblk.name, result))

                post_conversion_devices.append(
                  models.VdoConversionPostDevice(name=lsblk.name,
                                                 complete=(not result),
                                                 check_failed=(failure is not None),
                                                 failure=failure))

    return models.VdoConversionInfo(pre_conversion=pre_conversion_devices,
                                    post_conversion=post_conversion_devices,
                                    undetermined_conversion=undetermined_conversion_devices)
