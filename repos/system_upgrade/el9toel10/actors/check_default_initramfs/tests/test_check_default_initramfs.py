import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import check_default_initramfs
from leapp.libraries.common import testutils
from leapp.models import DefaultInitramfsInfo
from leapp.utils.report import is_inhibitor


def test_no_default_initramfs_info(monkeypatch):
    """Test that StopActorExecutionError is raised when no DefaultInitramfsInfo is provided."""
    # Mock api.consume to return empty iterator
    actor_mock = testutils.CurrentActorMocked(msgs=[])
    monkeypatch.setattr(check_default_initramfs.api, 'current_actor', actor_mock)

    with pytest.raises(StopActorExecutionError):
        check_default_initramfs.check_default_initramfs()


def test_initramfs_without_network_legacy(monkeypatch):
    """Test that no report is created when network-legacy module is not present."""
    # Create a DefaultInitramfsInfo without the problematic module
    initramfs_info = DefaultInitramfsInfo(
        path='/boot/initramfs-upgrade.x86_64.img',
        used_dracut_modules=['bash', 'systemd', 'kernel-modules', 'resume']
    )

    actor_mock = testutils.CurrentActorMocked(msgs=[initramfs_info])
    create_report_mock = testutils.create_report_mocked()

    monkeypatch.setattr(check_default_initramfs.api, 'current_actor', actor_mock)
    monkeypatch.setattr(check_default_initramfs.reporting, 'create_report', create_report_mock)

    check_default_initramfs.check_default_initramfs()

    # No report should be created
    assert not create_report_mock.called


def test_initramfs_with_network_legacy_without_config_file(monkeypatch):
    """
    Test that a report is created when network-legacy module is present but config file doesn't exist.

    The typical location of the config file (/etc/dracut.conf.d/50-network-legacy.conf) that
    adds the 'network-legacy' module is not present.
    """
    # Create a DefaultInitramfsInfo with the problematic module
    initramfs_info = DefaultInitramfsInfo(
        path='/boot/initramfs-upgrade.x86_64.img',
        used_dracut_modules=['bash', 'systemd', 'network-legacy', 'kernel-modules']
    )

    actor_mock = testutils.CurrentActorMocked(msgs=[initramfs_info])
    create_report_mock = testutils.create_report_mocked()

    monkeypatch.setattr(check_default_initramfs.api, 'current_actor', actor_mock)
    monkeypatch.setattr(check_default_initramfs.reporting, 'create_report', create_report_mock)
    # Mock os.path.exists to return False for the config file
    monkeypatch.setattr(check_default_initramfs.os.path, 'exists', lambda path: False)

    check_default_initramfs.check_default_initramfs()

    assert create_report_mock.called
    assert len(create_report_mock.reports) == 1

    report = create_report_mock.reports[0]

    assert is_inhibitor(report)

    report_resources = report['detail'].get('related_resources', [])
    assert not report_resources


def test_initramfs_with_network_legacy_with_config_file(monkeypatch):
    """Test that a report with related resource is created when network-legacy module and config file are present."""
    initramfs_info = DefaultInitramfsInfo(
        path='/boot/initramfs-upgrade.x86_64.img',
        used_dracut_modules=['bash', 'systemd', 'network-legacy', 'kernel-modules']
    )

    actor_mock = testutils.CurrentActorMocked(msgs=[initramfs_info])
    create_report_mock = testutils.create_report_mocked()

    monkeypatch.setattr(check_default_initramfs.api, 'current_actor', actor_mock)
    monkeypatch.setattr(check_default_initramfs.reporting, 'create_report', create_report_mock)

    def mock_exists(path):
        if path == '/etc/dracut.conf.d/50-network-legacy.conf':
            return True
        return os.path.exists(path)  # Fall back to original implementation since it is used in pytest internally

    monkeypatch.setattr(check_default_initramfs.os.path, 'exists', mock_exists)

    check_default_initramfs.check_default_initramfs()

    assert create_report_mock.called
    assert len(create_report_mock.reports) == 1

    report = create_report_mock.reports[0]
    assert is_inhibitor(report)

    report_resources = report['detail'].get('related_resources', [])
    assert report_resources
