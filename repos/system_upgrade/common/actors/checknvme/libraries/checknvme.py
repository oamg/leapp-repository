import os
from collections import defaultdict
from typing import List

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    DracutModule,
    KernelCmdline,
    KernelCmdlineArg,
    LiveModeConfig,
    NVMEDevice,
    NVMEInfo,
    StorageInfo,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UpgradeKernelCmdlineArgTasks
)

FMT_LIST_SEPARATOR = '\n    - '
FABRICS_TRANSPORT_TYPES = ['fc', 'tcp', 'rdma']
BROKEN_TRANSPORT_TYPES = ['tcp', 'rdma']
SAFE_TRANSPORT_TYPES = ['pcie', 'fc']
RQ_RPMS_CONTAINER = [
    'dracut',
    'dracut-network',  # Adds dracut-nvmf module
    'iproute',
    'jq',
    'nvme-cli',
    'sed',
]


class NVMEDeviceCollection:
    def __init__(self):
        self.device_by_transport = defaultdict(list)

    def add_device(self, device: NVMEDevice):
        self.device_by_transport[device.transport].append(device)

    def add_devices(self, devices: List[NVMEDevice]):
        for device in devices:
            self.add_device(device)

    def get_devices_by_transport(self, transport: str) -> List[NVMEDevice]:
        return self.device_by_transport[transport]

    @property
    def handled_transport_types(self) -> List[str]:
        return SAFE_TRANSPORT_TYPES

    @property
    def unhandled_devices(self) -> List[NVMEDevice]:
        unhandled_devices = []
        for transport, devices in self.device_by_transport.items():
            if transport not in self.handled_transport_types:
                unhandled_devices.extend(devices)
        return unhandled_devices

    @property
    def fabrics_devices(self) -> List[NVMEDevice]:
        fabrics_devices = []
        for transport in FABRICS_TRANSPORT_TYPES:
            fabrics_devices.extend(self.device_by_transport[transport])

        return fabrics_devices


def _format_list(data, sep=FMT_LIST_SEPARATOR, callback_sort=sorted, limit=0):
    # NOTE(pstodulk): Teaser O:-> https://issues.redhat.com/browse/RHEL-126447

    def identity(values):
        return values

    if callback_sort is None:
        callback_sort = identity
    res = ['{}{}'.format(sep, item) for item in callback_sort(data)]
    if limit:
        return ''.join(res[:limit])
    return ''.join(res)


def is_livemode_enabled() -> bool:
    livemode_config = next(api.consume(LiveModeConfig), None)
    if livemode_config and livemode_config.is_enabled:
        return True
    return False


def get_current_cmdline_arg_value(arg_name: str):
    cmdline = next(api.consume(KernelCmdline), None)

    if not cmdline:
        raise StopActorExecutionError(
            'Failed to obtain message with information about current kernel cmdline'
        )

    for arg in cmdline.parameters:
        if arg.key == arg_name:
            return arg.value

    return None


def _report_native_multipath_required():
    """Report that NVMe native multipath must be enabled on RHEL 9 before the upgrade."""
    reporting.create_report([
        reporting.Title('NVMe native multipath must be enabled on the target system'),
        reporting.Summary(
            'The system is booted with "nvme_core.multipath=N" kernel command line argument, '
            'disabling native multipath for NVMe devices. However, native multipath '
            'is required to be used for NVMe over Fabrics (NVMeoF) on the target system. '
            'Regarding that it is required to update the system setup to use '
            'the native multipath before the in-place upgrade.'
        ),
        reporting.Remediation(hint=(
            'Enable native multipath for NVMe devices following the official '
            'documentation and reboot your system - see the attached link.'
        )),
        reporting.ExternalLink(
            url='https://red.ht/rhel-9-enabling-multipathing-on-nvme-devices',
            title='Enabling native multipathing on NVMe devices.'
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.FILESYSTEM]),
    ])


def _report_system_should_migrate_to_native_multipath():
    """
    Report that since RHEL 9, native NVMe multipath is the recommended multipath solution for NVMe.
    """
    reporting.create_report([
        reporting.Title('Native NVMe multipath is recommended on the target system.'),
        reporting.Summary(
            'In the case that the system is using dm-multipath on NVMe devices, '
            'it is recommended to use the native NVMe multipath instead. '
            'We recommend to update the system configuration after the in-place '
            'upgrade following the official documentation - see the attached link.'
        ),
        reporting.ExternalLink(
            url='https://red.ht/rhel-9-enabling-multipathing-on-nvme-devices',
            title='Enabling native multipathing on NVMe devices.'
        ),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.FILESYSTEM, reporting.Groups.POST]),
    ])


def _report_kernel_cmdline_might_be_modified_unnecessarily():
    """
    Report that we introduced nvme_core.multipath=N, which might not be necessary.

    We introduce nvme_core.multipath=N (unconditionally) during 8>9 upgrade. However,
    the introduction of the argument might not be always necessary, but we currently lack
    an implementation that would precisely identify when the argument is truly needed.
    """
    reporting.create_report([
        reporting.Title('Native NVMe multipath will be disabled on the target system.'),
        reporting.Summary(
            'To ensure system\'s storage layout remains consistent during the upgrade, native '
            'NVMe multipath will be disabled by adding nvme_core.multipath=N to the default boot entry. '
            'In the case that the system does not use multipath, the nvme_core.multipath=N should be manually '
            'removed from the target system\'s boot entry after the upgrade.'
        ),
        reporting.ExternalLink(
            url='https://red.ht/rhel-9-enabling-multipathing-on-nvme-devices',
            title='Enabling native multipathing on NVMe devices.'
        ),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.FILESYSTEM, reporting.Groups.POST]),
    ])


def _tasks_copy_files_into_container(nvme_device_collection: NVMEDeviceCollection):
    """
    Tasks needed to modify target userspace container and the upgrade initramfs.
    """
    # NOTE: prepared for future extension, as it's possible that we will need
    # to copy more files when starting to look at NVMe-(RDMA|TCP)
    copy_files = []

    if nvme_device_collection.fabrics_devices:
        # /etc/nvme/ is required only in case of NVMe-oF (PCIe drives are safe)
        copy_files.append(CopyFile(src='/etc/nvme/'))

    api.produce(TargetUserSpaceUpgradeTasks(
        copy_files=copy_files,
        install_rpms=RQ_RPMS_CONTAINER)
    )


def _tasks_for_kernel_cmdline(nvme_device_collection: NVMEDeviceCollection):
    upgrade_cmdline_args = []
    target_cmdline_args = []

    if not is_livemode_enabled():
        upgrade_cmdline_args.append(KernelCmdlineArg(key='rd.nvmf.discover', value='fc,auto'))

    # The nvme_core.multipath argument is used to disable native multipath for NVMeoF devices.
    nvme_core_mpath_arg_val = get_current_cmdline_arg_value('nvme_core.multipath')

    # FIXME(pstodulk): handle multi-controller NVMe-PCIe drives WITH multipath used by, e.g., Intel SSD DC P4500.
    # Essentially, we always append nvme_core.multipath=N to the kernel command line during an 8>9 upgrade. This also
    # includes basics setups where a simple NVMe drive is attached over PCIe without any multipath capabilities (think
    # of an ordinary laptops). When the user attempts to later perform a 9>10 upgrade, an inhibitor will be raised with
    # instructions to remove nvme_core.multipath=N introduced by us during the previous upgrade, which might be
    # confusing as they might never even heard of multipath. Right now, we just emit a report for the user to remove
    # nvme_core.multipath=N from the boot entry if multipath is not used. We should improve this behaviour in the
    # future so that we can precisely target when to introduce the argument.

    if get_source_major_version() == '8':
        # NOTE: it's expected kind of that for NVMeoF users always use multipath

        # If the system is already booted with nvme_core.multipath=?, do not change it
        # The value will be copied from the default boot entry.
        # On the other, on 8>9 we want to always add this as there native multipath was unsupported
        # on RHEL 8, therefore, we should not need it (hence the value N).
        if not nvme_core_mpath_arg_val:
            upgrade_cmdline_args.append(KernelCmdlineArg(key='nvme_core.multipath', value='N'))
            target_cmdline_args.append(KernelCmdlineArg(key='nvme_core.multipath', value='N'))

        if nvme_core_mpath_arg_val != 'Y':
            # Print the report only if NVMeoF is detected and
            _report_system_should_migrate_to_native_multipath()
            _report_kernel_cmdline_might_be_modified_unnecessarily()

    if get_source_major_version() == '9':
        # NOTE(pstodulk): Check this always, does not matter whether we detect
        # NVMeoF or whether just PCIe is used. In any case, we will require user
        # to fix it.
        if nvme_core_mpath_arg_val == 'N':
            _report_native_multipath_required()
            return

    api.produce(UpgradeKernelCmdlineArgTasks(to_add=upgrade_cmdline_args))
    api.produce(TargetKernelCmdlineArgTasks(to_add=target_cmdline_args))


def register_upgrade_tasks(nvme_device_collection: NVMEDeviceCollection):
    """
    Register tasks that should happen during IPU to handle NVMe devices
    successfully.

    Args:
        nvme_fc_devices (list): List of NVMe-FC devices
    """
    _tasks_copy_files_into_container(nvme_device_collection)
    _tasks_for_kernel_cmdline(nvme_device_collection)


def report_missing_configs_for_fabrics_devices(nvme_info: NVMEInfo,
                                               nvme_device_collection: NVMEDeviceCollection,
                                               max_devices_in_report: int = 3) -> bool:
    missing_configs = []
    if not nvme_info.hostid:
        missing_configs.append('/etc/nvme/hostid')
    if not nvme_info.hostnqn:
        missing_configs.append('/etc/nvme/hostnqn')

    # NOTE(pstodulk): hostid and hostnqn are mandatory for NVMe-oF devices.
    # That means practically FC, RDMA, TCP. Let's inform user the upgrade
    # is blocked and they must configure the system properly to be able to
    # upgrade
    if not nvme_device_collection.fabrics_devices or not missing_configs:
        return  # We either have no fabrics devices or we have both hostid and hostnqn

    files_str = ', '.join(missing_configs) if missing_configs else 'required configuration files'

    device_names = [dev.name for dev in nvme_device_collection.fabrics_devices[:max_devices_in_report]]
    if len(nvme_device_collection.fabrics_devices) > max_devices_in_report:
        device_names.append('...')
    device_list_str = ', '.join(device_names)

    reporting.create_report([
        reporting.Title('Missing NVMe configuration files required for the upgrade'),
        reporting.Summary(
            'The system has NVMe-oF devices detected ({}), but {} are missing. '
            'Both /etc/nvme/hostid and /etc/nvme/hostnqn must be present and configured for NVMe-oF usage. '
            'Upgrade cannot continue until these files are provided.'.format(device_list_str, files_str)
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.FILESYSTEM]),
        reporting.Remediation(
            hint='Ensure the files /etc/nvme/hostid and /etc/nvme/hostnqn are present and properly configured.'
        ),
    ])


def get_devices_present_in_fstab() -> List[str]:
    storage_info = next(api.consume(StorageInfo), None)

    if not storage_info:
        raise StopActorExecutionError('Failed to obtain message with information about fstab entries')

    # Call realpath to get the *canonical* path to the device (user might use disk UUIDs, etc. in fstab)
    return {os.path.realpath(entry.fs_spec) for entry in storage_info.fstab}


def check_unhandled_devices_present_in_fstab(nvme_device_collection: NVMEDeviceCollection) -> bool:
    """Check if any unhandled NVMe devices are present in fstab.

    Args:
        nvme_device_collection: NVMEDeviceCollection instance

    Returns:
        True if any unhandled NVMe devices are present in fstab, False otherwise
    """
    unhandled_dev_nodes = {os.path.join('/dev', device.name) for device in nvme_device_collection.unhandled_devices}
    fstab_listed_dev_nodes = set(get_devices_present_in_fstab())

    required_unhandled_dev_nodes = unhandled_dev_nodes.intersection(fstab_listed_dev_nodes)
    if required_unhandled_dev_nodes:
        summary = (
            'The system has NVMe devices with a transport type that is currently '
            'not handled during the upgrade process present in fstab. Problematic devices: {0}'
        ).format(_format_list(required_unhandled_dev_nodes))

        reporting.create_report([
            reporting.Title('NVMe devices with unhandled transport type present in fstab'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.FILESYSTEM]),
        ])
        return True
    return False


def process():
    nvmeinfo = next(api.consume(NVMEInfo), None)
    if not nvmeinfo or not nvmeinfo.devices:
        return  # Nothing to do

    nvme_device_collection = NVMEDeviceCollection()
    nvme_device_collection.add_devices(nvmeinfo.devices)

    check_unhandled_devices_present_in_fstab(nvme_device_collection)
    report_missing_configs_for_fabrics_devices(nvmeinfo, nvme_device_collection)
    register_upgrade_tasks(nvme_device_collection)
