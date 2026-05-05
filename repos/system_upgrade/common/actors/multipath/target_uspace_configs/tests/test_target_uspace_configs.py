import os
import shutil

import pytest

from leapp.libraries.actor import target_uspace_multipath_configs as actor_lib
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    MultipathConfigUpdatesInfo,
    MultipathInfo,
    TargetUserSpaceUpgradeTasks,
    UpdatedMultipathConfig,
    UpgradeInitramfsTasks
)


@pytest.mark.parametrize(
    ('multipath_info', 'should_produce'),
    [
        (None, False),  # No multipath info message
        (MultipathInfo(is_configured=False), False),  # Multipath is not configured
        (MultipathInfo(is_configured=True, config_dir='/etc/multipath/conf.d'), True)
    ]
)
def test_production_conditions(monkeypatch, multipath_info, should_produce):
    """ Test whether messages are produced under right conditions. """
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    msgs = [multipath_info] if multipath_info else []
    if multipath_info and multipath_info.is_configured:
        update = UpdatedMultipathConfig(
            updated_config_location='/var/lib/leapp/proposed_changes/etc/multipath/conf.d/config.conf',
            target_path='/etc/multipath/conf.d/config.conf'
        )
        msgs.append(MultipathConfigUpdatesInfo(updates=[update]))

    actor_mock = CurrentActorMocked(msgs=msgs)
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    def listdir_mock(path):
        assert path == '/etc/multipath/conf.d'
        return ['config.conf', 'config-not-to-be-touched.conf']

    def exists_mock(path):
        return path == '/etc/multipath/conf.d'

    monkeypatch.setattr(os.path, 'exists', exists_mock)
    monkeypatch.setattr(os, 'listdir', listdir_mock)

    actor_lib.process()

    if should_produce:
        _target_uspace_tasks = [
            msg for msg in produce_mock.model_instances if isinstance(msg, TargetUserSpaceUpgradeTasks)
        ]
        assert len(_target_uspace_tasks) == 1

        target_uspace_tasks = _target_uspace_tasks[0]

        copies = sorted((copy.src, copy.dst) for copy in target_uspace_tasks.copy_files)
        expected_copies = [
            (
                '/etc/multipath.conf',
                '/etc/multipath.conf'
            ),
            (
                '/var/lib/leapp/proposed_changes/etc/multipath/conf.d/config.conf',
                '/etc/multipath/conf.d/config.conf'
            ),
            (
                '/etc/multipath/conf.d/config-not-to-be-touched.conf',
                '/etc/multipath/conf.d/config-not-to-be-touched.conf'
            )
        ]
        assert copies == sorted(expected_copies)

        _upgrade_initramfs_tasks = [m for m in produce_mock.model_instances if isinstance(m, UpgradeInitramfsTasks)]
        assert len(_upgrade_initramfs_tasks) == 1
        upgrade_initramfs_tasks = _upgrade_initramfs_tasks[0]

        dracut_modules = [dracut_mod.name for dracut_mod in upgrade_initramfs_tasks.include_dracut_modules]
        assert dracut_modules == ['multipath']
    else:
        assert not produce_mock.called


def test_file_locations_copied(monkeypatch):
    """Test that bindings/wwids/prkeys files are copied to target userspace."""
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    multipath_info = MultipathInfo(
        is_configured=True,
        config_dir='/etc/multipath/conf.d',
        bindings_file='/etc/multipath/bindings',
        wwids_file='/etc/multipath/wwids',
        prkeys_file='/etc/multipath/prkeys',
    )
    msgs = [multipath_info, MultipathConfigUpdatesInfo(updates=[])]
    actor_mock = CurrentActorMocked(msgs=msgs)
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    existing_files = {
        '/etc/multipath/conf.d',
        '/etc/multipath/bindings',
        '/etc/multipath/wwids',
        '/etc/multipath/prkeys',
    }

    def exists_mock(path):
        return path in existing_files

    monkeypatch.setattr(os.path, 'exists', exists_mock)
    monkeypatch.setattr(os, 'listdir', lambda path: [])

    actor_lib.process()

    _target_uspace_tasks = [
        msg for msg in produce_mock.model_instances if isinstance(msg, TargetUserSpaceUpgradeTasks)
    ]
    assert len(_target_uspace_tasks) == 1

    copies = {(copy.src, copy.dst) for copy in _target_uspace_tasks[0].copy_files}
    assert ('/etc/multipath/bindings', '/etc/multipath/bindings') in copies
    assert ('/etc/multipath/wwids', '/etc/multipath/wwids') in copies
    assert ('/etc/multipath/prkeys', '/etc/multipath/prkeys') in copies


def test_file_locations_not_copied_when_missing(monkeypatch):
    """Test that non-existent files are not copied."""
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    multipath_info = MultipathInfo(
        is_configured=True,
        config_dir='/etc/multipath/conf.d',
        bindings_file='/etc/multipath/bindings',
    )
    msgs = [multipath_info, MultipathConfigUpdatesInfo(updates=[])]
    actor_mock = CurrentActorMocked(msgs=msgs)
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    def exists_mock(path):
        return path == '/etc/multipath/conf.d'

    monkeypatch.setattr(os.path, 'exists', exists_mock)
    monkeypatch.setattr(os, 'listdir', lambda path: [])

    actor_lib.process()

    _target_uspace_tasks = [
        msg for msg in produce_mock.model_instances if isinstance(msg, TargetUserSpaceUpgradeTasks)
    ]
    assert len(_target_uspace_tasks) == 1

    copies = {copy.src for copy in _target_uspace_tasks[0].copy_files}
    # bindings_file doesn't exist on disk, so should not be copied
    assert '/etc/multipath/bindings' not in copies


def test_file_locations_overridden_by_updates(monkeypatch):
    """Test that UpdatedMultipathConfig entries override file copy sources."""
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    multipath_info = MultipathInfo(
        is_configured=True,
        config_dir='/etc/multipath/conf.d',
        bindings_file='/etc/multipath/bindings',
    )
    # The patcher says to move /tmp/bindings -> /etc/multipath/bindings
    update = UpdatedMultipathConfig(
        updated_config_location='/tmp/bindings',
        target_path='/etc/multipath/bindings'
    )
    msgs = [multipath_info, MultipathConfigUpdatesInfo(updates=[update])]
    actor_mock = CurrentActorMocked(msgs=msgs)
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    existing_files = {
        '/etc/multipath/conf.d',
        '/etc/multipath/bindings',
    }

    def exists_mock(path):
        return path in existing_files

    monkeypatch.setattr(os.path, 'exists', exists_mock)
    monkeypatch.setattr(os, 'listdir', lambda path: [])

    actor_lib.process()

    _target_uspace_tasks = [
        msg for msg in produce_mock.model_instances if isinstance(msg, TargetUserSpaceUpgradeTasks)
    ]
    assert len(_target_uspace_tasks) == 1

    copies = {(copy.src, copy.dst) for copy in _target_uspace_tasks[0].copy_files}
    # Original bindings file should be removed and replaced by the update source
    assert ('/etc/multipath/bindings', '/etc/multipath/bindings') not in copies
    assert ('/tmp/bindings', '/etc/multipath/bindings') in copies
