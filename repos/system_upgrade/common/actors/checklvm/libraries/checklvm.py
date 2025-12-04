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
        'Beginning with RHEL 9, LVM devices file is used by default to select devices used by '
        f'LVM. Since leapp detected the use of LVM filter in the {LVM_CONFIG_PATH} configuration '
        'file, the configuration won\'t be modified to use devices file during the upgrade and '
        'the LVM filter will remain in use after the upgrade.'
    )

    remediation_hint = (
        'While not required, switching to the LVM devices file from the LVM filter is possible '
        'using the following command. The command uses the existing LVM filter to create the system.devices '
        'file which is then used instead of the LVM filter. Before running the command, '
        f'make sure that \'use_devicesfile=1\' is set in {LVM_CONFIG_PATH}.'
    )
    remediation_command = ['vgimportdevices']

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=remediation_hint, commands=[remediation_command]),
        reporting.ExternalLink(
            title='Limiting LVM device visibility and usage',
            url='https://red.ht/limiting-lvm-devices-visibility-and-usage',
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

    copy_files = []
    api.current_logger().debug('Copying "{}" to the target userspace.'.format(LVM_CONFIG_PATH))
    copy_files.append(CopyFile(src=LVM_CONFIG_PATH))

    if lvm_devices_file_exists and lvm_config.devices.use_devicesfile:
        api.current_logger().debug('Copying "{}" to the target userspace.'.format(lvm_devices_file_path))
        copy_files.append(CopyFile(src=lvm_devices_file_path))

    api.produce(TargetUserSpaceUpgradeTasks(copy_files=copy_files))
