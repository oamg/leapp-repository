import contextlib

from leapp.libraries.actor import tus_layout


class _FakeInputs:
    def __init__(self, storage_info=None, target_iso=None):
        self.storage_info = storage_info
        self.target_iso = target_iso


class _FakeOverlay:
    def __init__(self, events):
        self.target = '/overlay/target'
        self._events = events

    def nspawn(self):
        return _FakeNspawn(self._events)


class _FakeNspawn:
    def __init__(self, events):
        self._events = events

    def __enter__(self):
        self._events.append('nspawn-enter')
        return self

    def __exit__(self, *args):
        self._events.append('nspawn-exit')
        return False


class _FakeIso:
    def __init__(self, events):
        self._events = events

    def __enter__(self):
        self._events.append('iso-enter')
        return self

    def __exit__(self, *args):
        self._events.append('iso-exit')
        return False


def test_compute_default_paths(monkeypatch):
    monkeypatch.setattr(tus_layout, 'get_env', lambda name, default: default)
    monkeypatch.setattr(tus_layout, 'get_target_major_version', lambda: '9')
    monkeypatch.setattr(tus_layout.overlaygen, 'get_recommended_leapp_free_space', lambda path: 2048)

    layout = tus_layout.compute()

    assert layout.container_root == '/var/lib/leapp'
    assert layout.userspace_path == '/var/lib/leapp/el9userspace'
    assert layout.scratch_dir == '/var/lib/leapp/scratch'
    assert layout.mounts_dir == '/var/lib/leapp/scratch/mounts'
    assert layout.installroot_overlay_mountpoint == '/el9target'
    assert layout.persistent_pkg_cache_path == '/var/lib/leapp/persistent_package_cache'
    assert layout.scratch_reserve == 2048


def test_compute_honours_container_root_override(monkeypatch):
    envs = {'LEAPP_CONTAINER_ROOT': '/custom/root'}
    monkeypatch.setattr(tus_layout, 'get_env', envs.get)
    monkeypatch.setattr(tus_layout, 'get_target_major_version', lambda: '10')
    monkeypatch.setattr(tus_layout.overlaygen, 'get_recommended_leapp_free_space', lambda path: 0)

    layout = tus_layout.compute()

    assert layout.container_root == '/custom/root'
    assert layout.userspace_path == '/custom/root/el10userspace'
    assert layout.scratch_dir == '/custom/root/scratch'
    assert layout.installroot_overlay_mountpoint == '/el10target'


def test_compute_passes_userspace_path_to_free_space_helper(monkeypatch):
    captured = {}
    monkeypatch.setattr(tus_layout, 'get_env', lambda name, default: default)
    monkeypatch.setattr(tus_layout, 'get_target_major_version', lambda: '9')
    monkeypatch.setattr(tus_layout.overlaygen, 'get_recommended_leapp_free_space',
                        lambda path: captured.setdefault('path', path) or 1)

    tus_layout.compute()

    assert captured['path'] == '/var/lib/leapp/el9userspace'


def _mock_layout():
    return tus_layout.Layout(
        container_root='/var/lib/leapp',
        userspace_path='/var/lib/leapp/el9userspace',
        scratch_dir='/var/lib/leapp/scratch',
        mounts_dir='/var/lib/leapp/scratch/mounts',
        installroot_overlay_mountpoint='/el9target',
        persistent_pkg_cache_path='/var/lib/leapp/persistent_package_cache',
        scratch_reserve=1234,
    )


def test_scratch_container_nesting_and_teardown_order(monkeypatch):
    events = []

    @contextlib.contextmanager
    def fake_create_source_overlay(**kwargs):
        events.append('overlay-enter')
        try:
            yield _FakeOverlay(events)
        finally:
            events.append('overlay-exit')

    def fake_mount_iso(root_dir, target_iso):
        return _FakeIso(events)

    monkeypatch.setattr(tus_layout.overlaygen, 'create_source_overlay', fake_create_source_overlay)
    monkeypatch.setattr(tus_layout.mounting, 'mount_upgrade_iso_to_root_dir', fake_mount_iso)

    inputs = _FakeInputs(storage_info=object(), target_iso=None)

    with tus_layout.scratch_container(_mock_layout(), inputs) as scratch:
        assert isinstance(scratch, _FakeNspawn)
        events.append('body')

    # Current nesting: overlay -> nspawn -> iso ; torn down in reverse.
    assert events == [
        'overlay-enter', 'nspawn-enter', 'iso-enter',
        'body',
        'iso-exit', 'nspawn-exit', 'overlay-exit',
    ]


def test_scratch_container_passes_storage_and_reserve_to_overlay(monkeypatch):
    captured = {}

    @contextlib.contextmanager
    def fake_create_source_overlay(**kwargs):
        captured.update(kwargs)
        yield _FakeOverlay([])

    monkeypatch.setattr(tus_layout.overlaygen, 'create_source_overlay', fake_create_source_overlay)
    monkeypatch.setattr(tus_layout.mounting, 'mount_upgrade_iso_to_root_dir',
                        lambda root, iso: _FakeIso([]))

    storage = object()
    inputs = _FakeInputs(storage_info=storage, target_iso=None)

    with tus_layout.scratch_container(_mock_layout(), inputs):
        pass

    assert captured['storage_info'] is storage
    assert captured['scratch_reserve'] == 1234
    assert captured['mounts_dir'] == '/var/lib/leapp/scratch/mounts'
    assert captured['scratch_dir'] == '/var/lib/leapp/scratch'
