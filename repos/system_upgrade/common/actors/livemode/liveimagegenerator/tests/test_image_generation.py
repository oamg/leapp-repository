import collections
import os
import shutil

import pytest

from leapp.libraries.actor import liveimagegenerator as live_image_generator_lib
from leapp.libraries.common import mounting
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import LiveModeArtifacts, LiveModeConfig, TargetUserSpaceInfo


def test_squafs_creation(monkeypatch):
    userspace_info = TargetUserSpaceInfo(path='/USERSPACE', scratch='/SCRATCH', mounts='/MOUNTS')
    livemode_config = LiveModeConfig(is_enabled=True, squashfs_fullpath='/var/lib/leapp/squashfs.img')

    def exists_mock(path):
        assert path == '/var/lib/leapp/squashfs.img'
        return True

    monkeypatch.setattr(os.path, 'exists', exists_mock)

    def unlink_mock(path):
        assert path == '/var/lib/leapp/squashfs.img'

    monkeypatch.setattr(os, 'unlink', unlink_mock)

    commands_executed = []

    def run_mock(command):
        commands_executed.append(command[0])

    monkeypatch.setattr(live_image_generator_lib, 'run', run_mock)

    live_image_generator_lib.build_squashfs(livemode_config, userspace_info)
    assert commands_executed == ['mksquashfs']


def test_userspace_lightening(monkeypatch):

    removed_trees = []

    def rmtree_mock(path):
        removed_trees.append(path)

    monkeypatch.setattr(shutil, 'rmtree', rmtree_mock)

    _ContextMock = collections.namedtuple('ContextMock', ('base_dir'))
    context_mock = _ContextMock(base_dir='/USERSPACE')

    live_image_generator_lib.lighten_target_userpace(context_mock)

    assert removed_trees == ['/USERSPACE/artifacts', '/USERSPACE/boot']


@pytest.mark.parametrize(
    ('livemode_config', 'should_produce'),
    (
        (LiveModeConfig(is_enabled=True, squashfs_fullpath='/squashfs'), True),
        (LiveModeConfig(is_enabled=False, squashfs_fullpath='/squashfs'), False),
        (None, False),
    )
)
def test_generate_live_image_if_enabled(monkeypatch, livemode_config, should_produce):
    userspace_info = TargetUserSpaceInfo(path='/USERSPACE', scratch='/SCRATCH', mounts='/MOUNTS')
    messages = [livemode_config, userspace_info] if livemode_config else [userspace_info]
    actor_mock = CurrentActorMocked(msgs=messages)
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    class NspawnMock(object):
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self, *args, **kwargs):
            pass

        def __exit__(self, *args, **kwargs):
            pass

    def build_squashfs_image_mock(livemode_config, userspace_info, *args, **kwargs):
        return '/squashfs'

    monkeypatch.setattr(mounting, 'NspawnActions', NspawnMock)
    monkeypatch.setattr(live_image_generator_lib, 'lighten_target_userpace', lambda context: None)
    monkeypatch.setattr(live_image_generator_lib, 'build_squashfs', build_squashfs_image_mock)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    live_image_generator_lib.generate_live_image_if_enabled()

    if should_produce:
        assert api.produce.called
        assert len(api.produce.model_instances) == 1
        artifacts = api.produce.model_instances[0]
        assert isinstance(artifacts, LiveModeArtifacts)
        assert artifacts.squashfs_path == '/squashfs'
    else:
        assert not api.produce.called
