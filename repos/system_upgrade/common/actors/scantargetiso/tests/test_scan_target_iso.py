import contextlib
import os
from functools import partial

import pytest

from leapp.libraries.actor import scan_target_os_iso
from leapp.libraries.common.mounting import MountError
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import CustomTargetRepository, TargetOSInstallationImage


def fail_if_called(fail_reason, *args, **kwargs):
    assert False, fail_reason


def test_determine_rhel_version_determination_unexpected_iso_structure_or_invalid_mountpoint(monkeypatch):
    iso_mountpoint = '/some/mountpoint'

    run_mocked = partial(fail_if_called,
                         'No commands should be called when mounted ISO mountpoint has unexpected structure.')
    monkeypatch.setattr(scan_target_os_iso, 'run', run_mocked)

    def isdir_mocked(path):
        assert path == '/some/mountpoint/BaseOS/Packages', 'Only the contents of BaseOS/Packages should be examined.'
        return False

    monkeypatch.setattr(os.path, 'isdir', isdir_mocked)

    determined_version = scan_target_os_iso.determine_rhel_version_from_iso_mountpoint(iso_mountpoint)
    assert not determined_version


def test_determine_rhel_version_valid_iso(monkeypatch):
    iso_mountpoint = '/some/mountpoint'

    def isdir_mocked(path):
        return True

    def listdir_mocked(path):
        assert path == '/some/mountpoint/BaseOS/Packages', 'Only the contents of BaseOS/Packages should be examined.'
        return ['xz-5.2.4-4.el8_6.x86_64.rpm',
                'libmodman-2.0.1-17.el8.i686.rpm',
                'redhat-release-8.7-0.3.el8.x86_64.rpm',
                'redhat-release-eula-8.7-0.3.el8.x86_64.rpm']

    def run_mocked(cmd, *args, **kwargs):
        rpm2cpio_output = 'rpm2cpio_output'
        if cmd[0] == 'rpm2cpio':
            assert cmd == ['rpm2cpio', '/some/mountpoint/BaseOS/Packages/redhat-release-8.7-0.3.el8.x86_64.rpm']
            return {'stdout': rpm2cpio_output}
        if cmd[0] == 'cpio':
            assert cmd == ['cpio', '--extract', '--to-stdout', './etc/redhat-release']
            assert kwargs['stdin'] == rpm2cpio_output
            return {'stdout': 'Red Hat Enterprise Linux Server release 7.9 (Maipo)'}
        raise ValueError('Unexpected command has been called.')

    monkeypatch.setattr(os.path, 'isdir', isdir_mocked)
    monkeypatch.setattr(os, 'listdir', listdir_mocked)
    monkeypatch.setattr(scan_target_os_iso, 'run', run_mocked)

    determined_version = scan_target_os_iso.determine_rhel_version_from_iso_mountpoint(iso_mountpoint)
    assert determined_version == '7.9'


def test_determine_rhel_version_valid_iso_no_rh_release(monkeypatch):
    iso_mountpoint = '/some/mountpoint'

    def isdir_mocked(path):
        return True

    def listdir_mocked(path):
        assert path == '/some/mountpoint/BaseOS/Packages', 'Only the contents of BaseOS/Packages should be examined.'
        return ['xz-5.2.4-4.el8_6.x86_64.rpm',
                'libmodman-2.0.1-17.el8.i686.rpm',
                'redhat-release-eula-8.7-0.3.el8.x86_64.rpm']

    run_mocked = partial(fail_if_called, 'No command should be called if the redhat-release package is not present.')

    monkeypatch.setattr(os.path, 'isdir', isdir_mocked)
    monkeypatch.setattr(os, 'listdir', listdir_mocked)
    monkeypatch.setattr(scan_target_os_iso, 'run', run_mocked)

    determined_version = scan_target_os_iso.determine_rhel_version_from_iso_mountpoint(iso_mountpoint)
    assert determined_version == ''


def test_determine_rhel_version_rpm_extract_fails(monkeypatch):
    iso_mountpoint = '/some/mountpoint'

    def isdir_mocked(path):
        return True

    def listdir_mocked(path):
        assert path == '/some/mountpoint/BaseOS/Packages', 'Only the contents of BaseOS/Packages should be examined.'
        return ['redhat-release-8.7-0.3.el8.x86_64.rpm']

    def run_mocked(cmd, *args, **kwargs):
        raise CalledProcessError(message='Ooops.', command=cmd, result=2)

    monkeypatch.setattr(os.path, 'isdir', isdir_mocked)
    monkeypatch.setattr(os, 'listdir', listdir_mocked)
    monkeypatch.setattr(scan_target_os_iso, 'run', run_mocked)

    determined_version = scan_target_os_iso.determine_rhel_version_from_iso_mountpoint(iso_mountpoint)
    assert determined_version == ''


@pytest.mark.parametrize('etc_rh_release_contents', ('',
                                                     'Red Hat Enterprise Linux Server',
                                                     'Fedora release 35 (Thirty Five)'))
def test_determine_rhel_version_unexpected_etc_rh_release_contents(monkeypatch, etc_rh_release_contents):
    iso_mountpoint = '/some/mountpoint'

    def isdir_mocked(path):
        return True

    def listdir_mocked(path):
        assert path == '/some/mountpoint/BaseOS/Packages', 'Only the contents of BaseOS/Packages should be examined.'
        return ['redhat-release-8.7-0.3.el8.x86_64.rpm']

    def run_mocked(cmd, *args, **kwargs):
        if cmd[0] == 'rpm2cpio':
            return {'stdout': 'rpm2cpio_output'}
        if cmd[0] == 'cpio':
            return {'stdout': etc_rh_release_contents}
        raise ValueError('Actor called an unexpected command: {0}'.format(cmd))

    monkeypatch.setattr(os.path, 'isdir', isdir_mocked)
    monkeypatch.setattr(os, 'listdir', listdir_mocked)
    monkeypatch.setattr(scan_target_os_iso, 'run', run_mocked)

    determined_version = scan_target_os_iso.determine_rhel_version_from_iso_mountpoint(iso_mountpoint)
    assert determined_version == ''


@pytest.mark.parametrize('iso_envar_set', (True, False))
def test_iso_detection_with_no_iso(monkeypatch, iso_envar_set):
    envars = {'LEAPP_TARGET_ISO': '/target_iso'} if iso_envar_set else {}
    mocked_actor = CurrentActorMocked(envars=envars)
    monkeypatch.setattr(api, 'current_actor', mocked_actor)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scan_target_os_iso.inform_ipu_about_request_to_use_target_iso()
    assert bool(api.produce.called) == iso_envar_set


def test_iso_mounting_failed(monkeypatch):
    envars = {'LEAPP_TARGET_ISO': '/target_iso'}
    mocked_actor = CurrentActorMocked(envars=envars)
    monkeypatch.setattr(api, 'current_actor', mocked_actor)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    def raise_mount_error_when_called():
        raise MountError('MountError')

    monkeypatch.setattr(scan_target_os_iso, 'LoopMount', raise_mount_error_when_called)

    scan_target_os_iso.inform_ipu_about_request_to_use_target_iso()
    assert api.produce.called

    assert len(api.produce.model_instances) == 1
    assert not api.produce.model_instances[0].was_mounted_successfully


@pytest.mark.parametrize(('repodirs_in_iso', 'expected_repoids'),
                         (((), ()),
                          (('BaseOS',), ('BaseOS',)),
                          (('BaseOS', 'AppStream'), ('BaseOS', 'AppStream')),
                          (('BaseOS', 'AppStream', 'UnknownRepo'), ('BaseOS', 'AppStream'))))
def test_iso_repository_detection(monkeypatch, repodirs_in_iso, expected_repoids):
    iso_path = '/target_iso'
    envars = {'LEAPP_TARGET_ISO': iso_path}
    mocked_actor = CurrentActorMocked(envars=envars)

    @contextlib.contextmanager
    def always_successful_loop_mount(*args, **kwargs):
        yield

    def mocked_os_path_exits(path):
        if path == iso_path:
            return True
        raise ValueError('Only the ISO path should be probed for existence.')

    def mocked_os_listdir(path):
        # Add some extra files as an ISO will always have some extra files in / as the ones parametrizing this test
        return list(repodirs_in_iso + ('eula.txt', 'grub', 'imgs'))

    monkeypatch.setattr(api, 'current_actor', mocked_actor)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(scan_target_os_iso, 'LoopMount', always_successful_loop_mount)
    monkeypatch.setattr(os.path, 'exists', mocked_os_path_exits)
    monkeypatch.setattr(os, 'listdir', mocked_os_listdir)
    monkeypatch.setattr(scan_target_os_iso, 'determine_rhel_version_from_iso_mountpoint', lambda iso_mountpoint: '7.9')

    scan_target_os_iso.inform_ipu_about_request_to_use_target_iso()

    produced_msgs = api.produce.model_instances
    assert len(produced_msgs) == 1 + len(expected_repoids)

    produced_custom_repo_msgs = []
    target_iso_msg = None
    for produced_msg in produced_msgs:
        if isinstance(produced_msg, CustomTargetRepository):
            produced_custom_repo_msgs.append(produced_msg)
        else:
            assert not target_iso_msg, 'Actor is expected to produce only one TargetOSInstallationImage msg'
            target_iso = produced_msg

    # Do not explicitly instantiate model instances of what we expect the model instance to look like. Instead check
    # for expected structural properties, leaving the actor implementation flexibility (e.g. choice of the mountpoint)
    iso_mountpoint = target_iso.mountpoint

    assert target_iso.was_mounted_successfully
    assert target_iso.rhel_version == '7.9'

    expected_repos = {(repoid, 'file://' + os.path.join(iso_mountpoint, repoid)) for repoid in expected_repoids}
    actual_repos = {(repo.repoid, repo.baseurl) for repo in produced_custom_repo_msgs}
    assert expected_repos == actual_repos
