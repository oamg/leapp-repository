import contextlib
import io

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_contentaccess
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepositoryFile, RHSMInfo


class _Inputs(object):
    """Minimal stand-in for tus_inputdata.InputData holding only what establish() reads."""

    def __init__(self, rhui_info=None, rhsm_info=None, skip_rhsm=False, custom_repofiles=None):
        self.rhui_info = rhui_info
        self.rhsm_info = rhsm_info
        self.skip_rhsm = skip_rhsm
        self.custom_repofiles = custom_repofiles or []


class _FakeContext(object):
    """Minimal stand-in for the mounting.IsolatedActions scratch context."""

    def __init__(self, calls=None):
        # Shared ordered log of side effects, used to assert step order.
        self._calls = calls if calls is not None else []
        self.copied_to = []
        self.written = {}

    def copy_to(self, src, dst):
        self._calls.append('custom')
        self.copied_to.append((src, dst))

    @contextlib.contextmanager
    def open(self, path, mode='r'):
        buf = io.StringIO()
        yield buf
        self.written[path] = buf.getvalue()
        self._calls.append('stream')


class _FailingContext(object):
    """Context whose open() raises, to exercise the write error path."""

    def __init__(self, exc):
        self._exc = exc

    @contextlib.contextmanager
    def open(self, path, mode='r'):
        raise self._exc
        yield None  # unreachable; only present to make this a generator


def _patch_collaborators(monkeypatch, calls, distro='rhel', captured=None):
    """
    Drive the config getters via a mocked current_actor and stub the external
    collaborators establish() delegates to (recording call order into ``calls``).
    """
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(dst_ver='9.6', dst_distro=distro))

    def _fake_swap(*args):
        if captured is not None:
            captured['swap_args'] = args
        calls.append('rhui')

    monkeypatch.setattr(tus_contentaccess.tus_rhui, 'perform_client_swap', _fake_swap)
    monkeypatch.setattr(tus_contentaccess.rhsm, 'set_container_mode',
                        lambda ctx: calls.append('container_mode'))
    monkeypatch.setattr(tus_contentaccess.rhsm, 'switch_certificate',
                        lambda ctx, info: calls.append('switch_cert'))


@pytest.mark.parametrize(
    ('rhui_info', 'distro', 'custom_files', 'expected_calls', 'expected_written', 'expected_copied'),
    [
        # Full CentOS flow: RHUI swap -> container mode -> switch cert -> $stream -> custom.
        (
            object(), 'centos', ['/etc/custom.repo'],
            ['rhui', 'container_mode', 'switch_cert', 'stream', 'custom'],
            {'/etc/dnf/vars/stream': '9-stream\n'},
            [('/etc/custom.repo', '/etc/yum.repos.d/custom.repo')],
        ),
        # RHEL target, no RHUI, no custom repofiles: no swap, no $stream, no copies.
        (
            None, 'rhel', [],
            ['container_mode', 'switch_cert'],
            {},
            [],
        ),
        # CentOS target without RHUI still writes the $stream variable.
        (
            None, 'centos', [],
            ['container_mode', 'switch_cert', 'stream'],
            {'/etc/dnf/vars/stream': '9-stream\n'},
            [],
        ),
        # Non-RHEL/CentOS target (e.g. almalinux) must not write the $stream variable.
        (
            None, 'almalinux', [],
            ['container_mode', 'switch_cert'],
            {},
            [],
        ),
        # Multiple custom repofiles are copied by basename, preserving order.
        (
            None, 'rhel', ['/etc/a.repo', '/some/nested/path/b.repo'],
            ['container_mode', 'switch_cert', 'custom', 'custom'],
            {},
            [
                ('/etc/a.repo', '/etc/yum.repos.d/a.repo'),
                ('/some/nested/path/b.repo', '/etc/yum.repos.d/b.repo'),
            ],
        ),
    ],
)
def test_establish(monkeypatch, rhui_info, distro, custom_files, expected_calls,
                   expected_written, expected_copied):
    calls = []
    _patch_collaborators(monkeypatch, calls, distro=distro)
    context = _FakeContext(calls)
    inputs = _Inputs(
        rhui_info=rhui_info,
        rhsm_info=RHSMInfo(existing_product_certificates=[]),
        custom_repofiles=[CustomTargetRepositoryFile(file=f) for f in custom_files],
    )

    tus_contentaccess.establish(context, inputs)

    assert calls == expected_calls
    assert context.written == expected_written
    assert context.copied_to == expected_copied


@pytest.mark.parametrize('skip_rhsm', [False, True])
def test_establish_passes_expected_arguments_to_rhui_swap(monkeypatch, skip_rhsm):
    calls = []
    captured = {}
    _patch_collaborators(monkeypatch, calls, distro='rhel', captured=captured)
    rhui_info = object()
    context = _FakeContext(calls)
    inputs = _Inputs(
        rhui_info=rhui_info,
        rhsm_info=RHSMInfo(existing_product_certificates=[]),
        skip_rhsm=skip_rhsm,
    )

    tus_contentaccess.establish(context, inputs)

    # perform_client_swap(context, rhui_info, releasever, skip_rhsm)
    assert captured['swap_args'] == (context, rhui_info, '9.6', skip_rhsm)


def test_establish_propagates_missing_target_certificate(monkeypatch):
    calls = []
    _patch_collaborators(monkeypatch, calls, distro='rhel')

    def _boom(ctx, info):
        raise rhsm.MissingTargetProductCertificate(message='missing cert')

    monkeypatch.setattr(tus_contentaccess.rhsm, 'switch_certificate', _boom)
    context = _FakeContext(calls)
    inputs = _Inputs(rhsm_info=RHSMInfo(existing_product_certificates=[]))

    # establish() must NOT catch this - it propagates to the orchestrator (inhibitor #1).
    with pytest.raises(rhsm.MissingTargetProductCertificate):
        tus_contentaccess.establish(context, inputs)


@pytest.mark.parametrize(('target_major', 'varfile'), [
    ('9', '/etc/dnf/vars/stream'),
    ('10', '/custom/path/stream'),
])
def test_adjust_dnf_stream_variable_writes_target_value(target_major, varfile):
    context = _FakeContext()

    tus_contentaccess._adjust_dnf_stream_variable(context, target_major, varfile=varfile)

    assert context.written == {varfile: '{}-stream\n'.format(target_major)}


@pytest.mark.parametrize('exc', [OSError('disk full'), FileNotFoundError('missing dir')])
def test_adjust_dnf_stream_variable_raises_on_write_error(exc):
    context = _FailingContext(exc)

    with pytest.raises(StopActorExecutionError):
        tus_contentaccess._adjust_dnf_stream_variable(context, '9')
