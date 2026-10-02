import contextlib

from leapp.libraries.actor import tus_layout


class _FakeOverlay(object):
    def __init__(self, events):
        self.target = '/overlay/target'
        self._events = events


class _FakeIso(object):
    def __init__(self, events):
        self._events = events

    def __enter__(self):
        self._events.append('iso-enter')
        return self

    def __exit__(self, *args):
        self._events.append('iso-exit')
        return False


class _FakeNspawn(object):
    def __init__(self, events):
        self._events = events

    def __enter__(self):
        self._events.append('nspawn-enter')
        return self

    def __exit__(self, *args):
        self._events.append('nspawn-exit')
        return False


class _FakeContext(object):
    """Minimal IsolatedActions stand-in recording the operations invoked on it."""

    def __init__(self):
        self.copied_to = []
        self.copied_from = []
        self.removed_trees = []
        self.made_dirs = []
        self._existing_dirs = set()

    def makedirs(self, path, mode=0o777, exists_ok=True):
        self.made_dirs.append(path)

    def remove_tree(self, path):
        self.removed_trees.append(path)

    def copytree_to(self, src, dst):
        self.copied_to.append((src, dst))

    def copytree_from(self, src, dst):
        self.copied_from.append((src, dst))

    def full_path(self, path):
        return '/overlay' + path


def _mock_layout():
    return tus_layout.Layout(
        container_root='/var/lib/leapp',
        target_major='9',
        userspace_path='/var/lib/leapp/el9userspace',
        scratch_dir='/var/lib/leapp/scratch',
        mounts_dir='/var/lib/leapp/scratch/mounts',
        scratch_reserve=1234,
    )


def test_compute_default_paths(monkeypatch):
    monkeypatch.setattr(tus_layout, 'get_env', lambda name, default: default)
    monkeypatch.setattr(tus_layout, 'get_target_major_version', lambda: '9')
    monkeypatch.setattr(tus_layout.overlaygen, 'get_recommended_leapp_free_space', lambda path: 2048)

    layout = tus_layout.compute()

    assert layout.container_root == '/var/lib/leapp'
    assert layout.userspace_path == '/var/lib/leapp/el9userspace'
    assert layout.scratch_dir == '/var/lib/leapp/scratch'
    assert layout.mounts_dir == '/var/lib/leapp/scratch/mounts'
    assert layout.scratch_reserve == 2048


def test_compute_honours_container_root_override(monkeypatch):
    envs = {'LEAPP_CONTAINER_ROOT': '/custom/root'}
    monkeypatch.setattr(tus_layout, 'get_env', lambda name, default: envs.get(name, default))
    monkeypatch.setattr(tus_layout, 'get_target_major_version', lambda: '10')
    monkeypatch.setattr(tus_layout.overlaygen, 'get_recommended_leapp_free_space', lambda path: 0)

    layout = tus_layout.compute()

    assert layout.container_root == '/custom/root'
    assert layout.userspace_path == '/custom/root/el10userspace'
    assert layout.scratch_dir == '/custom/root/scratch'


def test_scratch_container_nesting_and_teardown_order(monkeypatch):
    events = []

    @contextlib.contextmanager
    def fake_create_source_overlay(**kwargs):
        events.append('overlay-enter')
        overlay = _FakeOverlay(events)
        overlay.nspawn = lambda: _FakeNspawn(events)
        try:
            yield overlay
        finally:
            events.append('overlay-exit')

    def fake_mount_iso(root_dir, target_iso):
        return _FakeIso(events)

    monkeypatch.setattr(tus_layout.overlaygen, 'create_source_overlay', fake_create_source_overlay)
    monkeypatch.setattr(tus_layout.mounting, 'mount_upgrade_iso_to_root_dir', fake_mount_iso)

    inputs = type('I', (), {'xfs_presence': None, 'storage_info': None, 'target_iso': None})()

    with tus_layout.scratch_container(_mock_layout(), inputs) as scratch:
        assert isinstance(scratch, _FakeNspawn)
        events.append('body')

    assert events == [
        'overlay-enter', 'iso-enter', 'nspawn-enter',
        'body',
        'nspawn-exit', 'iso-exit', 'overlay-exit',
    ]


def test_persistent_cache_disabled_is_noop(monkeypatch):
    monkeypatch.setattr(tus_layout, 'get_env', lambda name, default: '0')
    context = _FakeContext()

    tus_layout.persistent_cache_pull(context, _mock_layout(), '/installroot')
    tus_layout.persistent_cache_push(context, _mock_layout(), '/installroot')

    assert context.copied_to == []
    assert context.copied_from == []


def test_persistent_cache_pull_when_enabled(monkeypatch):
    monkeypatch.setattr(tus_layout, 'get_env', lambda name, default: '1')
    monkeypatch.setattr(tus_layout.os.path, 'isdir', lambda p: True)
    context = _FakeContext()

    tus_layout.persistent_cache_pull(context, _mock_layout(), '/installroot')

    assert context.copied_to == [
        ('/var/lib/leapp/el9_persistent_package_cache', '/installroot/var/cache/dnf')
    ]
    assert context.removed_trees == ['/installroot/var/cache/dnf']
