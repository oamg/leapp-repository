import os

import pytest

from leapp import reporting
from leapp.libraries.actor import check_target_iso
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository, FstabEntry, StorageInfo, TargetOSInstallationImage
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize('mount_successful', (True, False))
def test_inhibit_on_iso_mount_failure(monkeypatch, mount_successful):
    create_report_mock = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mock)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    target_iso_msg = TargetOSInstallationImage(path='',
                                               mountpoint='',
                                               repositories=[],
                                               was_mounted_successfully=mount_successful)

    check_target_iso.inhibit_if_failed_to_mount_iso(target_iso_msg)

    expected_report_count = 0 if mount_successful else 1
    assert create_report_mock.called == expected_report_count
    if not mount_successful:
        assert is_inhibitor(create_report_mock.reports[0])


@pytest.mark.parametrize(('detected_iso_rhel_ver', 'required_target_ver', 'should_inhibit'),
                         (('8.6', '8.6', False), ('7.9', '8.6', True), ('8.5', '8.6', False), ('', '8.6', True)))
def test_inhibit_on_detected_rhel_version(monkeypatch, detected_iso_rhel_ver, required_target_ver, should_inhibit):
    create_report_mock = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mock)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver=required_target_ver))

    target_iso_msg = TargetOSInstallationImage(path='',
                                               mountpoint='',
                                               repositories=[],
                                               rhel_version=detected_iso_rhel_ver,
                                               was_mounted_successfully=True)

    check_target_iso.inhibit_if_wrong_iso_rhel_version(target_iso_msg)

    expected_report_count = 1 if should_inhibit else 0
    assert create_report_mock.called == expected_report_count
    if should_inhibit:
        assert is_inhibitor(create_report_mock.reports[0])


@pytest.mark.parametrize(('iso_repoids', 'should_inhibit'),
                         ((('BaseOS', 'AppStream'), False), (('BaseOS',), True), (('AppStream',), True), ((), True)))
def test_inhibit_on_invalid_rhel_version(monkeypatch, iso_repoids, should_inhibit):
    create_report_mock = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mock)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    iso_repositories = [CustomTargetRepository(repoid=repoid, baseurl='', name='') for repoid in iso_repoids]

    target_iso_msg = TargetOSInstallationImage(path='',
                                               mountpoint='',
                                               repositories=iso_repositories,
                                               was_mounted_successfully=True)

    check_target_iso.inihibit_if_iso_does_not_contain_basic_repositories(target_iso_msg)

    expected_report_count = 1 if should_inhibit else 0
    assert create_report_mock.called == expected_report_count
    if should_inhibit:
        assert is_inhibitor(create_report_mock.reports[0])


def test_inhibit_on_nonexistent_iso(monkeypatch):
    iso_path = '/nonexistent/iso'
    create_report_mock = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mock)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    def mocked_os_path_exists(path):
        assert path == iso_path, 'The actor should check only the path to ISO for existence.'
        return False

    monkeypatch.setattr(os.path, 'exists', mocked_os_path_exists)

    target_iso_msg = TargetOSInstallationImage(path=iso_path,
                                               mountpoint='',
                                               repositories=[],
                                               was_mounted_successfully=True)

    check_target_iso.inhibit_if_not_valid_iso_file(target_iso_msg)

    assert create_report_mock.called == 1
    assert is_inhibitor(create_report_mock.reports[0])


@pytest.mark.parametrize(('filetype', 'should_inhibit'),
                         (('{path}: text/plain; charset=us-ascii', True),
                          ('{path}: application/x-iso9660-image; charset=binary', False)))
def test_inhibit_on_path_not_pointing_to_iso(monkeypatch, filetype, should_inhibit):
    iso_path = '/path/not-an-iso'
    create_report_mock = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mock)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    def mocked_os_path_exists(path):
        assert path == iso_path, 'The actor should check only the path to ISO for existence.'
        return True

    def mocked_run(cmd, *args, **kwargs):
        assert cmd[0] == 'file', 'The actor should only use `file` cmd when checking for file type.'
        return {'stdout': filetype.format(path=iso_path)}

    monkeypatch.setattr(os.path, 'exists', mocked_os_path_exists)
    monkeypatch.setattr(check_target_iso, 'run', mocked_run)

    target_iso_msg = TargetOSInstallationImage(path=iso_path, mountpoint='', repositories=[])

    check_target_iso.inhibit_if_not_valid_iso_file(target_iso_msg)

    if should_inhibit:
        assert create_report_mock.called == 1
        assert is_inhibitor(create_report_mock.reports[0])
    else:
        assert create_report_mock.called == 0


@pytest.mark.parametrize('is_persistently_mounted', (False, True))
def test_inhibition_when_iso_not_on_persistent_partition(monkeypatch, is_persistently_mounted):
    path_mountpoint = '/d0/d1'
    iso_path = '/d0/d1/d2/d3/iso'
    create_report_mock = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mock)

    def os_path_ismount_mocked(path):
        if path == path_mountpoint:
            return True
        if path == '/':  # / Should be a mountpoint on every system
            return True
        return False

    monkeypatch.setattr(os.path, 'ismount', os_path_ismount_mocked)

    fstab_mountpoint = path_mountpoint if is_persistently_mounted else '/some/other/mountpoint'
    fstab_entry = FstabEntry(fs_spec='/dev/sta2', fs_file=fstab_mountpoint,
                             fs_vfstype='', fs_mntops='', fs_freq='', fs_passno='')
    storage_info_msg = StorageInfo(fstab=[fstab_entry])

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[storage_info_msg]))

    target_iso_msg = TargetOSInstallationImage(path=iso_path, mountpoint='', repositories=[])
    check_target_iso.inhibit_if_iso_not_located_on_persistent_partition(target_iso_msg)

    if is_persistently_mounted:
        assert not create_report_mock.called
    else:
        assert create_report_mock.called == 1
        assert is_inhibitor(create_report_mock.reports[0])


def test_actor_does_not_perform_when_iso_not_used(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    check_target_iso.perform_target_iso_checks()

    assert not reporting.create_report.called
