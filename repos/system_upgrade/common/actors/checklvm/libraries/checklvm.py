import os

from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    DistributionSignedRPM,
    DracutModule,
    LVMConfig,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks
)

LVM_CONFIG_PATH = '/etc/lvm/lvm.conf'
LVM_DEVICES_FILE_PATH_PREFIX = '/etc/lvm/devices'


def _report_filter_detection():
    title = 'LVM filter definition detected.'
    summary = (
        'RHEL 9 and above uses the LVM devices file by default to select devices used by LVM. '
        f'Since this system has LVM filter defined in the {LVM_CONFIG_PATH}, it will be '
        'used after the upgrade as well.'
    )

    remediation_hint = (
        'While not mandatory, switching to the LVM devices file from the LVM filter is possible '
        'using the following command. It uses the existing LVM filter to create the system.devices '
        'file which is then used instead of the LVM filter as long as it exists. Before running the command, '
        'make sure that the use_devicesfile=1 (default for RHEL 9 and above).'
    )
    remediation_command = ['vgimportdevices', '-a']

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=remediation_hint, commands=[remediation_command]),
        reporting.ExternalLink(
            title='Limiting LVM device visibility and usage',
            url='https://red.ht/3MfgK7c',
        ),
        reporting.Severity(reporting.Severity.INFO),
    ])


def check_lvm():
    if not has_package(DistributionSignedRPM, 'lvm2'):
        return

    lvm_config = next(api.consume(LVMConfig), None)
    if not lvm_config:
        return

    lvm_devices_file_path = os.path.join(LVM_DEVICES_FILE_PATH_PREFIX, lvm_config.devices.devicesfile)
    lvm_devices_file_exists = os.path.isfile(lvm_devices_file_path)

    filters_used = not lvm_config.devices.use_devicesfile or not lvm_devices_file_exists
    if filters_used:
        _report_filter_detection()

    api.current_logger().debug('Including lvm dracut module.')
    api.produce(UpgradeInitramfsTasks(include_dracut_modules=[DracutModule(name='lvm')]))
    # TODO: decide if we need to install lvm2 package in the container as well

    copy_files = []
    api.current_logger().debug('Copying "{}" to the target userspace.'.format(LVM_CONFIG_PATH))
    copy_files.append(CopyFile(src=LVM_CONFIG_PATH))

    if lvm_devices_file_exists and lvm_config.devices.use_devicesfile:
        api.current_logger().debug('Copying "{}" to the target userspace.'.format(lvm_devices_file_path))
        copy_files.append(CopyFile(src=lvm_devices_file_path))

    api.produce(TargetUserSpaceUpgradeTasks(copy_files=copy_files))
