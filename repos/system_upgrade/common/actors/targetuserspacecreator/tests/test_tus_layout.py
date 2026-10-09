import os

import pytest

from leapp.libraries.actor import tus_layout

_SENTINEL_RESERVE = 4242


class MockGetEnv:
    """Mock for get_env honoring an optional override for LEAPP_CONTAINER_ROOT."""

    def __init__(self, override=None):
        self.override = override
        self.calls = []

    def __call__(self, name, default=None):
        self.calls.append((name, default))
        if self.override is not None:
            return self.override
        return default


class MockGetRecommendedFreeSpace:
    """Mock for overlaygen.get_recommended_leapp_free_space."""

    def __init__(self, reserve):
        self.reserve = reserve
        self.called_with = []

    def __call__(self, userspace_path):
        self.called_with.append(userspace_path)
        return self.reserve


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


class MockInputs:
    """Minimal stand-in for the InputData value object."""

    def __init__(self, storage_info, target_iso):
        self.storage_info = storage_info
        self.target_iso = target_iso


def _target_major():
    return '9'


@pytest.mark.parametrize(
    ('override', 'container_root'),
    [
        (None, '/var/lib/leapp'),
        ('/custom/root', '/custom/root'),
    ]
)
def test_compute_layout(monkeypatch, override, container_root):
    get_env = MockGetEnv(override=override)
    free_space = MockGetRecommendedFreeSpace(_SENTINEL_RESERVE)
    monkeypatch.setattr(tus_layout, 'get_env', get_env)
    monkeypatch.setattr(tus_layout, 'get_target_major_version', _target_major)
    monkeypatch.setattr(tus_layout.overlaygen, 'get_recommended_leapp_free_space', free_space)

    layout = tus_layout.compute()

    assert get_env.calls == [('LEAPP_CONTAINER_ROOT', '/var/lib/leapp')]
    assert layout.container_root == container_root
    assert layout.userspace_path == os.path.join(container_root, 'el9userspace')
    assert layout.scratch_dir == os.path.join(container_root, 'scratch')
    assert layout.mounts_dir == os.path.join(container_root, 'scratch', 'mounts')
    assert layout.installroot_overlay_mountpoint == '/el9target'
    assert layout.persistent_pkg_cache_path == os.path.join(container_root, 'persistent_package_cache')
    assert layout.scratch_reserve == _SENTINEL_RESERVE
    assert free_space.called_with == [layout.userspace_path]


def test_scratch_container(monkeypatch):
    scratch = MockScratch()
    overlay = MockOverlay(scratch)
    create_overlay = MockCreateSourceOverlay(overlay)
    mount_iso = MockMountIso()
    monkeypatch.setattr(tus_layout.overlaygen, 'create_source_overlay', create_overlay)
    monkeypatch.setattr(tus_layout.mounting, 'mount_upgrade_iso_to_root_dir', mount_iso)

    layout = tus_layout.Layout(
        container_root='/var/lib/leapp',
        userspace_path='/var/lib/leapp/el9userspace',
        scratch_dir='/var/lib/leapp/scratch',
        mounts_dir='/var/lib/leapp/scratch/mounts',
        installroot_overlay_mountpoint='/el9target',
        persistent_pkg_cache_path='/var/lib/leapp/persistent_package_cache',
        scratch_reserve=1234,
    )
    inputs = MockInputs(storage_info='STORAGE_INFO', target_iso='TARGET_ISO')

    with tus_layout.scratch_container(layout, inputs) as yielded:
        assert yielded is scratch
        assert overlay.entered is True
        assert overlay.nspawn_called is True
        assert scratch.entered is True
        assert mount_iso.entered is True
        assert overlay.exited is False
        assert scratch.exited is False
        assert mount_iso.exited is False

    assert create_overlay.kwargs == {
        'mounts_dir': '/var/lib/leapp/scratch/mounts',
        'scratch_dir': '/var/lib/leapp/scratch',
        'xfs_info': None,
        'storage_info': 'STORAGE_INFO',
        'scratch_reserve': 1234,
    }
    assert mount_iso.called_with == ('OVERLAY_TARGET', 'TARGET_ISO')
    assert mount_iso.exited is True
    assert scratch.exited is True
    assert overlay.exited is True
