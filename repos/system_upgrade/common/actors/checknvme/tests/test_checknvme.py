"""
Unit tests for checknvme actor

Skip isort as it's kind of broken when mixing grid import and one line imports

isort:skip_file
"""

import pytest

from leapp.libraries.actor import checknvme
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    DracutModule,
    KernelCmdlineArg,
    NVMEDevice,
    NVMEInfo,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UpgradeKernelCmdlineArgTasks
)


def test_no_nvme_devices(monkeypatch):
    """Test when no NVMe devices are present."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
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

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[nvme_info]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checknvme.process()

    # Should produce TargetUserSpaceUpgradeTasks and UpgradeInitramfsTasks but not UpgradeKernelCmdlineArgTasks
    assert api.produce.called == 2

    produced_msgs = api.produce.model_instances
    assert any(isinstance(msg, TargetUserSpaceUpgradeTasks) for msg in produced_msgs)
    assert any(isinstance(msg, UpgradeInitramfsTasks) for msg in produced_msgs)
    assert not any(isinstance(msg, UpgradeKernelCmdlineArgTasks) for msg in produced_msgs)


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

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[nvme_info]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checknvme.process()

    # Should produce all three message types including UpgradeKernelCmdlineArgTasks
    assert api.produce.called == 3

    produced_msgs = api.produce.model_instances
    assert any(isinstance(msg, TargetUserSpaceUpgradeTasks) for msg in produced_msgs)
    assert any(isinstance(msg, UpgradeInitramfsTasks) for msg in produced_msgs)

    # Check that UpgradeKernelCmdlineArgTasks was produced with correct argument
    kernel_cmdline_msgs = [msg for msg in produced_msgs if isinstance(msg, UpgradeKernelCmdlineArgTasks)]
    assert len(kernel_cmdline_msgs) == 1

    kernel_cmdline_msg = kernel_cmdline_msgs[0]
    assert len(kernel_cmdline_msg.to_add) == 1

    cmdline_arg = kernel_cmdline_msg.to_add[0]
    assert cmdline_arg.key == 'rd.nvmf.discover'
    assert cmdline_arg.value == 'fc,auto'


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

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[nvme_info]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checknvme.process()

    # Should produce all three message types
    assert api.produce.called == 3

    produced_msgs = api.produce.model_instances

    # Check that UpgradeKernelCmdlineArgTasks was produced
    kernel_cmdline_msgs = [msg for msg in produced_msgs if isinstance(msg, UpgradeKernelCmdlineArgTasks)]
    assert len(kernel_cmdline_msgs) == 1

    cmdline_arg = kernel_cmdline_msgs[0].to_add[0]
    assert cmdline_arg.key == 'rd.nvmf.discover'
    assert cmdline_arg.value == 'fc,auto'


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

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[nvme_info]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checknvme.process()

    # Should still produce only one UpgradeKernelCmdlineArgTasks message
    kernel_cmdline_msgs = [msg for msg in api.produce.model_instances
                           if isinstance(msg, UpgradeKernelCmdlineArgTasks)]
    assert len(kernel_cmdline_msgs) == 1

    # Should still have only one kernel argument
    assert len(kernel_cmdline_msgs[0].to_add) == 1


def test_nvme_missing_hostid_hostnqn_blocks_upgrade(monkeypatch):
    """Test that missing hostid/hostnqn blocks upgrade for NVMe-oF devices."""
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

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[nvme_info]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checknvme.process()

    # Should not produce any upgrade tasks when upgrade is blocked
    assert api.produce.called == 0


def test_check_nvme_function_return_values():
    """Test the check_nvme function return values directly."""
    # Test with FC device
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

    upgrade_can_continue, nvme_fc_devices = checknvme.check_nvme(nvme_info)
    assert upgrade_can_continue is True
    assert nvme_fc_devices == [nvme_fc_device]


def test_register_upgrade_tasks_without_fc_devices(monkeypatch):
    """Test _register_upgrade_tasks without FC devices."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checknvme._register_upgrade_tasks(nvme_fc_devices=None)

    # Should produce 2 messages (TargetUserSpaceUpgradeTasks and UpgradeInitramfsTasks)
    assert api.produce.called == 2

    produced_msgs = api.produce.model_instances
    assert any(isinstance(msg, TargetUserSpaceUpgradeTasks) for msg in produced_msgs)
    assert any(isinstance(msg, UpgradeInitramfsTasks) for msg in produced_msgs)
    assert not any(isinstance(msg, UpgradeKernelCmdlineArgTasks) for msg in produced_msgs)


def test_register_upgrade_tasks_with_fc_devices(monkeypatch):
    """Test _register_upgrade_tasks with FC devices."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    nvme_fc_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='fc'
    )

    checknvme._register_upgrade_tasks(nvme_fc_devices=[nvme_fc_device])

    # Should produce 3 messages including UpgradeKernelCmdlineArgTasks
    assert api.produce.called == 3

    produced_msgs = api.produce.model_instances
    assert any(isinstance(msg, TargetUserSpaceUpgradeTasks) for msg in produced_msgs)
    assert any(isinstance(msg, UpgradeInitramfsTasks) for msg in produced_msgs)
    assert any(isinstance(msg, UpgradeKernelCmdlineArgTasks) for msg in produced_msgs)

    kernel_cmdline_msgs = [msg for msg in produced_msgs if isinstance(msg, UpgradeKernelCmdlineArgTasks)]
    assert len(kernel_cmdline_msgs) == 1

    cmdline_arg = kernel_cmdline_msgs[0].to_add[0]
    assert cmdline_arg.key == 'rd.nvmf.discover'
    assert cmdline_arg.value == 'fc,auto'
