import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_contentaccess
from leapp.libraries.common.testutils import logger_mocked


class MockFileHandle:
    def __init__(self, store, path):
        self._store = store
        self._path = path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def write(self, data):
        self._store[self._path] = self._store.get(self._path, '') + data


class MockContext:
    def __init__(self, open_raises=None):
        self.written_files = {}
        self.copied = []
        self._open_raises = open_raises

    def open(self, path, mode):
        if self._open_raises:
            raise self._open_raises
        return MockFileHandle(self.written_files, path)

    def copy_to(self, src, dst):
        self.copied.append((src, dst))


class MockRepoFile:
    def __init__(self, path):
        self.file = path


class MockInputData:
    def __init__(self, rhui_info=None, skip_rhsm=False, rhsm_info=None, custom_repofiles=None):
        self.rhui_info = rhui_info
        self.skip_rhsm = skip_rhsm
        self.rhsm_info = rhsm_info
        self.custom_repofiles = custom_repofiles or []


class CallSpy:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def test_adjust_dnf_stream_variable_writes():
    context = MockContext()
    tus_contentaccess._adjust_dnf_stream_variable(context, '9', varfile='/etc/dnf/vars/stream')
    assert context.written_files == {'/etc/dnf/vars/stream': '9-stream\n'}


@pytest.mark.parametrize('error', [OSError('disk error'), FileNotFoundError('missing')])
def test_adjust_dnf_stream_variable_error(error):
    context = MockContext(open_raises=error)
    with pytest.raises(StopActorExecutionError):
        tus_contentaccess._adjust_dnf_stream_variable(context, '9')
    assert not context.written_files


def test_install_custom_repofiles():
    context = MockContext()
    repofiles = [MockRepoFile('/home/user/a.repo'), MockRepoFile('/tmp/sub/b.repo')]
    tus_contentaccess._install_custom_repofiles(context, repofiles)
    assert context.copied == [
        ('/home/user/a.repo', '/etc/yum.repos.d/a.repo'),
        ('/tmp/sub/b.repo', '/etc/yum.repos.d/b.repo'),
    ]


def test_install_custom_repofiles_empty():
    context = MockContext()
    tus_contentaccess._install_custom_repofiles(context, [])
    assert not context.copied


def _setup_establish(monkeypatch, distro_id, swap_spy, set_container_spy, switch_cert_spy, target_major='9'):
    monkeypatch.setattr(tus_contentaccess, 'get_target_major_version', lambda: target_major)
    monkeypatch.setattr(tus_contentaccess, 'get_target_version', lambda: '9.6')
    monkeypatch.setattr(tus_contentaccess, 'get_target_distro_id', lambda: distro_id)
    monkeypatch.setattr(tus_contentaccess.tus_rhui, 'perform_client_swap', swap_spy)
    monkeypatch.setattr(tus_contentaccess.rhsm, 'set_container_mode', set_container_spy)
    monkeypatch.setattr(tus_contentaccess.rhsm, 'switch_certificate', switch_cert_spy)
    monkeypatch.setattr(tus_contentaccess.api, 'current_logger', logger_mocked())


def test_establish_centos_with_rhui(monkeypatch):
    context = MockContext()
    swap_spy = CallSpy()
    set_container_spy = CallSpy()
    switch_cert_spy = CallSpy()
    _setup_establish(monkeypatch, 'centos', swap_spy, set_container_spy, switch_cert_spy)

    rhui_info = object()
    rhsm_info = object()
    repofiles = [MockRepoFile('/tmp/custom.repo')]
    inputs = MockInputData(rhui_info=rhui_info, skip_rhsm=True, rhsm_info=rhsm_info,
                           custom_repofiles=repofiles)

    tus_contentaccess.establish(context, inputs)

    assert swap_spy.calls == [((context, rhui_info, '9.6', True), {})]
    assert switch_cert_spy.calls == [((context, rhsm_info), {})]
    assert len(set_container_spy.calls) == 1
    assert context.written_files == {'/etc/dnf/vars/stream': '9-stream\n'}
    assert context.copied == [('/tmp/custom.repo', '/etc/yum.repos.d/custom.repo')]


def test_establish_rhel_no_rhui(monkeypatch):
    context = MockContext()
    swap_spy = CallSpy()
    set_container_spy = CallSpy()
    switch_cert_spy = CallSpy()
    _setup_establish(monkeypatch, 'rhel', swap_spy, set_container_spy, switch_cert_spy, target_major='8')

    inputs = MockInputData(rhui_info=None, skip_rhsm=False, rhsm_info=object(), custom_repofiles=[])

    tus_contentaccess.establish(context, inputs)

    assert not swap_spy.calls
    assert len(set_container_spy.calls) == 1
    assert len(switch_cert_spy.calls) == 1
    assert not context.written_files
    assert not context.copied


def test_establish_rhel_with_rhui_no_stream(monkeypatch):
    context = MockContext()
    swap_spy = CallSpy()
    set_container_spy = CallSpy()
    switch_cert_spy = CallSpy()
    _setup_establish(monkeypatch, 'rhel', swap_spy, set_container_spy, switch_cert_spy)

    rhui_info = object()
    inputs = MockInputData(rhui_info=rhui_info, skip_rhsm=False, rhsm_info=object(), custom_repofiles=[])

    tus_contentaccess.establish(context, inputs)

    assert swap_spy.calls == [((context, rhui_info, '9.6', False), {})]
    assert not context.written_files
