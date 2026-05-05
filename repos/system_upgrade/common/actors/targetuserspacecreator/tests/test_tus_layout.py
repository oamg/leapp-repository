import os
from unittest import mock

import pytest
from test_tus_mock_utils import MockInputData

from leapp.libraries.actor import tus_layout
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api

_SENTINEL_RESERVE = 4242


class MockScratch:
    """Mock entered nspawn scratch context."""

    def __init__(self):
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args):
        self.exited = True
        return False


class MockOverlay:
    """Mock source overlay context manager yielding a scratch via nspawn()."""

    def __init__(self, scratch, target='OVERLAY_TARGET'):
        self.target = target
        self._scratch = scratch
        self.entered = False
        self.exited = False
        self.nspawn_called = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args):
        self.exited = True
        return False

    def nspawn(self):
        self.nspawn_called = True
        return self._scratch


class MockCreateSourceOverlay:
    """Mock for overlaygen.create_source_overlay recording its kwargs."""

    def __init__(self, overlay):
        self.overlay = overlay
        self.kwargs = None

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        return self.overlay


class MockMountIso:
    """Mock callable + context manager for mounting.mount_upgrade_iso_to_root_dir."""

    def __init__(self):
        self.entered = False
        self.exited = False
        self.called_with = None

    def __call__(self, target, target_iso):
        self.called_with = (target, target_iso)
        return self

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args):
        self.exited = True
        return False


def _target_major():
    return '9'


@pytest.mark.parametrize(('dst_ver', 'dst_maj_ver', 'container_root'), (
    ('9.6', '9', None),
    ('9.6', '9', '/foo/path/'),
    ('10', '10', None),

))
def test_compute_layout(monkeypatch, dst_ver, dst_maj_ver, container_root):
    envars = {'LEAPP_CONTAINER_ROOT': container_root} if container_root else None
    if not container_root:
        container_root = tus_layout._DEFAULT_CONTAINER_ROOT
    mocked_actor = CurrentActorMocked(dst_ver=dst_ver, envars=envars)
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    layout = tus_layout.compute()

    assert layout.container_root == container_root
    assert layout.userspace_path == os.path.join(container_root, f'el{dst_maj_ver}userspace')
    assert layout.scratch_dir == os.path.join(container_root, 'scratch')
    assert layout.mounts_dir == os.path.join(container_root, 'scratch', 'mounts')
    assert layout.installroot_overlay_mountpoint == f'/el{dst_maj_ver}target'
    assert layout.persistent_pkg_cache_path == os.path.join(container_root, 'persistent_package_cache')


def test_scratch_container(monkeypatch):
    scratch = MockScratch()
    overlay = MockOverlay(scratch)
    create_overlay = MockCreateSourceOverlay(overlay)
    free_space = mock.Mock(return_value=_SENTINEL_RESERVE)
    mount_iso = MockMountIso()
    monkeypatch.setattr(tus_layout.overlaygen, 'create_source_overlay', create_overlay)
    monkeypatch.setattr(tus_layout.overlaygen, 'get_recommended_leapp_free_space', free_space)
    monkeypatch.setattr(tus_layout.mounting, 'mount_upgrade_iso_to_root_dir', mount_iso)

    layout = tus_layout.Layout(
        container_root='/var/lib/leapp',
        userspace_path='/var/lib/leapp/el9userspace',
        scratch_dir='/var/lib/leapp/scratch',
        mounts_dir='/var/lib/leapp/scratch/mounts',
        installroot_overlay_mountpoint='/el9target',
        persistent_pkg_cache_path='/var/lib/leapp/persistent_package_cache',
        userspace_gpg_keys_dir='/leapp-trusted-gpg-keys',
    )
    inputs = MockInputData(storage_info='STORAGE_INFO', target_iso='TARGET_ISO')

    with tus_layout.scratch_container(layout, inputs) as yielded:
        assert yielded is scratch
        assert overlay.entered is True
        assert overlay.nspawn_called is True
        assert scratch.entered is True
        assert mount_iso.entered is True
        assert overlay.exited is False
        assert scratch.exited is False
        assert mount_iso.exited is False

    free_space.assert_called_once_with(layout.userspace_path)
    assert create_overlay.kwargs == {
        'mounts_dir': '/var/lib/leapp/scratch/mounts',
        'scratch_dir': '/var/lib/leapp/scratch',
        'xfs_info': None,
        'storage_info': 'STORAGE_INFO',
        'scratch_reserve': _SENTINEL_RESERVE,
    }
    assert mount_iso.called_with == ('OVERLAY_TARGET', 'TARGET_ISO')
    assert mount_iso.exited is True
    assert scratch.exited is True
    assert overlay.exited is True
