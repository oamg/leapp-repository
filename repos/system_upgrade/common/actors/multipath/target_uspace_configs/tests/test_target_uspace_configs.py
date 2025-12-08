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
