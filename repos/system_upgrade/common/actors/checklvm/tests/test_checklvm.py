import os

import pytest

from leapp.libraries.actor import checklvm
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    DistributionSignedRPM,
    LVMConfig,
    LVMConfigDevicesSection,
    RPM,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks
)


def test_check_lvm_when_lvm_not_installed(monkeypatch):
    def consume_mocked(model):
        if model == LVMConfig:
            assert False
        if model == DistributionSignedRPM:
            yield DistributionSignedRPM(items=[])

    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checklvm.check_lvm()

    assert not api.produce.called


@pytest.mark.parametrize(
    ('config', 'create_report', 'devices_file_exists'),
    [
        (LVMConfig(devices=LVMConfigDevicesSection(use_devicesfile=False)), True, False),
        (LVMConfig(devices=LVMConfigDevicesSection(use_devicesfile=True)), False, True),
        (LVMConfig(devices=LVMConfigDevicesSection(use_devicesfile=True)), True, False),
        (LVMConfig(devices=LVMConfigDevicesSection(use_devicesfile=False, devicesfile="test.devices")), True, False),
        (LVMConfig(devices=LVMConfigDevicesSection(use_devicesfile=True, devicesfile="test.devices")), False, True),
        (LVMConfig(devices=LVMConfigDevicesSection(use_devicesfile=True, devicesfile="test.devices")), True, False),
    ]
)
def test_scan_when_lvm_installed(monkeypatch, config, create_report, devices_file_exists):
    lvm_package = RPM(
        name='lvm2',
        version='2',
        release='1',
        epoch='1',
        packager='',
        arch='x86_64',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'
    )

    def isfile_mocked(_):
        return devices_file_exists

    def consume_mocked(model):
        if model == LVMConfig:
            yield config
        if model == DistributionSignedRPM:
            yield DistributionSignedRPM(items=[lvm_package])

    def report_filter_detection_mocked():
        assert create_report

    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)
    monkeypatch.setattr(os.path, 'isfile', isfile_mocked)
    monkeypatch.setattr(checklvm, '_report_filter_detection', report_filter_detection_mocked)

    checklvm.check_lvm()

    # The lvm is installed, thus the dracut module is enabled and at least the lvm.conf is copied
    assert api.produce.called == 2
    assert len(api.produce.model_instances) == 2

    expected_copied_files = [checklvm.LVM_CONFIG_PATH]
    if devices_file_exists and config.devices.use_devicesfile:
        devices_file_path = os.path.join(checklvm.LVM_DEVICES_FILE_PATH_PREFIX, config.devices.devicesfile)
        expected_copied_files.append(devices_file_path)

    for produced_model in api.produce.model_instances:
        assert isinstance(produced_model, (UpgradeInitramfsTasks, TargetUserSpaceUpgradeTasks))

        if isinstance(produced_model, UpgradeInitramfsTasks):
            assert len(produced_model.include_dracut_modules) == 1
            assert produced_model.include_dracut_modules[0].name == 'lvm'
        else:
            assert len(produced_model.copy_files) == len(expected_copied_files)
            for file in produced_model.copy_files:
                assert file.src in expected_copied_files
