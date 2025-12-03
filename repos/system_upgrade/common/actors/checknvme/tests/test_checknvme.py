import os

from leapp import reporting
from leapp.libraries.actor import checknvme
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    FstabEntry,
    KernelCmdline,
    NVMEDevice,
    NVMEInfo,
    StorageInfo,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.utils.report import is_inhibitor


def _make_storage_info(fstab_entries=None):
    """Helper to create StorageInfo with fstab entries."""
    if fstab_entries is None:
        fstab_entries = []
    return StorageInfo(fstab=fstab_entries)


def test_no_nvme_devices(monkeypatch):
    """Test when no NVMe devices are present."""
    msgs = [KernelCmdline(parameters=[])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checknvme.process()

    # No messages should be produced when no NVMe devices are present
    assert api.produce.called == 0


def test_nvme_pcie_devices_only(monkeypatch):
    """Test with only NVMe PCIe devices (no FC devices)."""
    nvme_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='pcie'
    )
    nvme_info = NVMEInfo(
        devices=[nvme_device],
        hostid='test-hostid',
        hostnqn='test-hostnqn'
    )

    msgs = [KernelCmdline(parameters=[]), nvme_info, _make_storage_info()]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(checknvme, '_report_system_should_migrate_to_native_multipath', lambda: None)
    monkeypatch.setattr(checknvme, '_report_kernel_cmdline_might_be_modified_unnecessarily', lambda: None)

    checknvme.process()

    def _get_produced_msg(msg_type):
        """Get a single produced message of the given type."""
        for msg in api.produce.model_instances:
            # We cannot use isinstance due to problems with inheritance
            if type(msg) is msg_type:  # pylint: disable=unidiomatic-typecheck
                return msg
        return None

    # Check TargetUserSpaceUpgradeTasks - no copy_files for PCIe-only
    userspace_tasks = _get_produced_msg(TargetUserSpaceUpgradeTasks)
    assert userspace_tasks.copy_files == []

    expected_pkgs = {'iproute', 'jq', 'nvme-cli', 'sed', 'dracut', 'dracut-network'}
    assert set(userspace_tasks.install_rpms) == expected_pkgs

    # Check UpgradeInitramfsTasks
    initramfs_tasks = _get_produced_msg(UpgradeInitramfsTasks)
    assert len(initramfs_tasks.include_dracut_modules) == 1
    assert initramfs_tasks.include_dracut_modules[0].name == 'nvmf'

    # Check UpgradeKernelCmdlineArgTasks
    upgrade_cmdline_tasks = _get_produced_msg(UpgradeKernelCmdlineArgTasks)
    upgrade_cmdline_args = {(arg.key, arg.value) for arg in upgrade_cmdline_tasks.to_add}
    assert ('rd.nvmf.discover', 'fc,auto') in upgrade_cmdline_args

    # Check TargetKernelCmdlineArgTasks
    target_cmdline_tasks = _get_produced_msg(TargetKernelCmdlineArgTasks)
    # For PCIe-only, no nvme_core.multipath arg is added (no fabrics devices)
    target_cmdline_args = {(arg.key, arg.value) for arg in target_cmdline_tasks.to_add}
    assert target_cmdline_args == set() or ('nvme_core.multipath', 'N') in target_cmdline_args


def test_nvme_fc_devices_present(monkeypatch):
    """Test with NVMe-FC devices present."""
    nvme_fc_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='fc'
    )
    nvme_info = NVMEInfo(
        devices=[nvme_fc_device],
        hostid='test-hostid',
        hostnqn='test-hostnqn'
    )

    msgs = [KernelCmdline(parameters=[]), nvme_info, _make_storage_info()]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(checknvme, '_report_system_should_migrate_to_native_multipath', lambda: None)
    monkeypatch.setattr(checknvme, '_report_kernel_cmdline_might_be_modified_unnecessarily', lambda: None)

    checknvme.process()

    assert api.produce.called == 4

    produced_msgs = api.produce.model_instances
    assert any(isinstance(msg, TargetUserSpaceUpgradeTasks) for msg in produced_msgs)
    assert any(isinstance(msg, UpgradeInitramfsTasks) for msg in produced_msgs)

    # Check that UpgradeKernelCmdlineArgTasks was produced with correct argument
    kernel_cmdline_msgs = [msg for msg in produced_msgs if isinstance(msg, UpgradeKernelCmdlineArgTasks)]
    assert len(kernel_cmdline_msgs) == 1

    cmdline_args = {(c_arg.key, c_arg.value) for c_arg in kernel_cmdline_msgs[0].to_add}
    expected_cmdline_args = {
        ('rd.nvmf.discover', 'fc,auto'),
        ('nvme_core.multipath', 'N')
    }
    assert expected_cmdline_args == cmdline_args


def test_mixed_nvme_devices(monkeypatch):
    """Test with mixed NVMe devices (PCIe and FC)."""
    nvme_pcie_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='pcie'
    )
    nvme_fc_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme1',
        name='nvme1',
        transport='fc'
    )
    nvme_info = NVMEInfo(
        devices=[nvme_pcie_device, nvme_fc_device],
        hostid='test-hostid',
        hostnqn='test-hostnqn'
    )

    msgs = [KernelCmdline(parameters=[]), nvme_info, _make_storage_info()]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(checknvme, '_report_system_should_migrate_to_native_multipath', lambda: None)
    monkeypatch.setattr(checknvme, '_report_kernel_cmdline_might_be_modified_unnecessarily', lambda: None)

    checknvme.process()

    assert api.produce.called == 4

    produced_msgs = api.produce.model_instances

    # Check that UpgradeKernelCmdlineArgTasks was produced
    kernel_cmdline_msgs = [msg for msg in produced_msgs if isinstance(msg, UpgradeKernelCmdlineArgTasks)]
    assert len(kernel_cmdline_msgs) == 1

    cmdline_args = {(c_arg.key, c_arg.value) for c_arg in kernel_cmdline_msgs[0].to_add}
    expected_cmdline_args = {
        ('rd.nvmf.discover', 'fc,auto'),
        ('nvme_core.multipath', 'N')
    }
    assert expected_cmdline_args == cmdline_args


def test_multiple_nvme_fc_devices(monkeypatch):
    """Test with multiple NVMe-FC devices."""
    nvme_fc_device1 = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='fc'
    )
    nvme_fc_device2 = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme1',
        name='nvme1',
        transport='fc'
    )
    nvme_info = NVMEInfo(
        devices=[nvme_fc_device1, nvme_fc_device2],
        hostid='test-hostid',
        hostnqn='test-hostnqn'
    )

    msgs = [KernelCmdline(parameters=[]), nvme_info, _make_storage_info()]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(checknvme, '_report_system_should_migrate_to_native_multipath', lambda: None)
    monkeypatch.setattr(checknvme, '_report_kernel_cmdline_might_be_modified_unnecessarily', lambda: None)

    checknvme.process()

    # Should still produce only one UpgradeKernelCmdlineArgTasks message
    kernel_cmdline_msgs = [msg for msg in api.produce.model_instances
                           if isinstance(msg, UpgradeKernelCmdlineArgTasks)]
    assert len(kernel_cmdline_msgs) == 1

    # Should still have only two kernel arguments
    assert len(kernel_cmdline_msgs[0].to_add) == 2


def test_nvme_missing_hostid_hostnqn_creates_inhibitor(monkeypatch):
    """Test that missing hostid/hostnqn creates an inhibitor report for NVMe-oF devices."""
    nvme_fc_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='fc'
    )
    # Missing hostid and hostnqn
    nvme_info = NVMEInfo(
        devices=[nvme_fc_device],
        hostid=None,
        hostnqn=None
    )

    msgs = [KernelCmdline(parameters=[]), nvme_info, _make_storage_info()]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checknvme, '_report_system_should_migrate_to_native_multipath', lambda: None)
    monkeypatch.setattr(checknvme, '_report_kernel_cmdline_might_be_modified_unnecessarily', lambda: None)

    checknvme.process()

    # Should create an inhibitor report for missing configs
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)


def test_nvme_device_collection_categorization():
    """Test NVMEDeviceCollection categorizes devices correctly."""
    nvme_pcie_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='pcie'
    )
    nvme_fc_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme1',
        name='nvme1',
        transport='fc'
    )
    nvme_tcp_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme2',
        name='nvme2',
        transport='tcp'
    )

    collection = checknvme.NVMEDeviceCollection()
    collection.add_devices([nvme_pcie_device, nvme_fc_device, nvme_tcp_device])

    assert nvme_pcie_device in collection.get_devices_by_transport('pcie')
    assert nvme_fc_device in collection.get_devices_by_transport('fc')
    assert nvme_tcp_device in collection.get_devices_by_transport('tcp')

    # FC and TCP are fabrics devices
    assert nvme_fc_device in collection.fabrics_devices
    assert nvme_tcp_device in collection.fabrics_devices
    assert nvme_pcie_device not in collection.fabrics_devices

    # TCP is unhandled (not in SAFE_TRANSPORT_TYPES)
    assert nvme_tcp_device in collection.unhandled_devices
    assert nvme_pcie_device not in collection.unhandled_devices
    assert nvme_fc_device not in collection.unhandled_devices


def test_register_upgrade_tasks_without_fabrics_devices(monkeypatch):
    """Test register_upgrade_tasks without fabrics devices."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    kernel_cmdline_tasks = KernelCmdline(parameters=[])
    msgs = [kernel_cmdline_tasks]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(checknvme, '_report_system_should_migrate_to_native_multipath', lambda: None)
    monkeypatch.setattr(checknvme, '_report_kernel_cmdline_might_be_modified_unnecessarily', lambda: None)

    nvme_pcie_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='pcie'
    )
    collection = checknvme.NVMEDeviceCollection()
    collection.add_device(nvme_pcie_device)

    checknvme.register_upgrade_tasks(collection)

    produced_msgs = api.produce.model_instances
    expected_msg_types = {
        TargetUserSpaceUpgradeTasks,
        UpgradeInitramfsTasks,
        UpgradeKernelCmdlineArgTasks,
        TargetKernelCmdlineArgTasks,
    }
    assert set(type(msg) for msg in produced_msgs) == expected_msg_types


def test_register_upgrade_tasks_with_fabrics_devices(monkeypatch):
    """Test register_upgrade_tasks with fabrics devices."""
    nvme_fc_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='fc'
    )
    collection = checknvme.NVMEDeviceCollection()
    collection.add_device(nvme_fc_device)

    msgs = [KernelCmdline(parameters=[])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(checknvme, '_report_system_should_migrate_to_native_multipath', lambda: None)
    monkeypatch.setattr(checknvme, '_report_kernel_cmdline_might_be_modified_unnecessarily', lambda: None)

    checknvme.register_upgrade_tasks(collection)

    produced_msgs = api.produce.model_instances
    expected_msg_types = {
        TargetUserSpaceUpgradeTasks,
        UpgradeInitramfsTasks,
        UpgradeKernelCmdlineArgTasks,
        TargetKernelCmdlineArgTasks,
    }
    assert set(type(msg) for msg in produced_msgs) == expected_msg_types

    kernel_cmdline_msgs = [msg for msg in produced_msgs if isinstance(msg, UpgradeKernelCmdlineArgTasks)]
    assert len(kernel_cmdline_msgs) == 1

    cmdline_args = {(c_arg.key, c_arg.value) for c_arg in kernel_cmdline_msgs[0].to_add}
    expected_cmdline_args = {
        ('rd.nvmf.discover', 'fc,auto'),
        ('nvme_core.multipath', 'N')
    }
    assert expected_cmdline_args == cmdline_args


def test_check_unhandled_devices_not_in_fstab(monkeypatch):
    """Test that no inhibitor is created when unhandled devices are not in fstab."""
    nvme_tcp_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='tcp'  # tcp is unhandled
    )
    collection = checknvme.NVMEDeviceCollection()
    collection.add_device(nvme_tcp_device)

    # fstab contains a different device
    fstab_entries = [
        FstabEntry(fs_spec='/dev/sda1', fs_file='/', fs_vfstype='ext4',
                   fs_mntops='defaults', fs_freq='1', fs_passno='1')
    ]
    storage_info = _make_storage_info(fstab_entries)

    msgs = [storage_info]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr('os.path.realpath', lambda path: path)

    result = checknvme.check_unhandled_devices_present_in_fstab(collection)

    assert result is False
    assert reporting.create_report.called == 0


def test_check_unhandled_devices_in_fstab_creates_inhibitor(monkeypatch):
    """Test that an inhibitor is created when unhandled devices are in fstab."""
    nvme_tcp_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='tcp'  # tcp is unhandled
    )
    collection = checknvme.NVMEDeviceCollection()
    collection.add_device(nvme_tcp_device)

    # fstab contains the unhandled device
    fstab_entries = [
        FstabEntry(fs_spec='/dev/nvme0', fs_file='/', fs_vfstype='ext4',
                   fs_mntops='defaults', fs_freq='1', fs_passno='1')
    ]
    storage_info = _make_storage_info(fstab_entries)

    msgs = [storage_info]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(os.path, 'realpath', lambda path: path)

    result = checknvme.check_unhandled_devices_present_in_fstab(collection)

    assert result is True
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)


def test_check_unhandled_devices_handled_device_in_fstab_no_inhibitor(monkeypatch):
    """Test that no inhibitor is created when only handled devices are in fstab."""
    nvme_pcie_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='pcie'  # pcie is handled
    )
    collection = checknvme.NVMEDeviceCollection()
    collection.add_device(nvme_pcie_device)

    # fstab contains the handled device
    fstab_entries = [
        FstabEntry(fs_spec='/dev/nvme0n1p1', fs_file='/', fs_vfstype='ext4',
                   fs_mntops='defaults', fs_freq='1', fs_passno='1')
    ]
    storage_info = _make_storage_info(fstab_entries)

    msgs = [storage_info]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr('os.path.realpath', lambda path: path)

    result = checknvme.check_unhandled_devices_present_in_fstab(collection)

    assert result is False
    assert reporting.create_report.called == 0
