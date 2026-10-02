import contextlib
import io

import pytest

from leapp.libraries.actor import tus_contentaccess
from leapp.libraries.common import rhsm
from leapp.models import CustomTargetRepositoryFile, RHSMInfo


class _Inputs(object):
    def __init__(self, rhui_info=None, rhsm_info=None, skip_rhsm=False, custom_repofiles=None):
        self.rhui_info = rhui_info
        self.rhsm_info = rhsm_info
        self.skip_rhsm = skip_rhsm
        self.custom_repofiles = custom_repofiles or []


class FakeContext(object):
    def __init__(self, events):
        self._events = events
        self.copied_to = []
        self.written = {}

    def full_path(self, path):
        return '/container' + path

    def copy_to(self, src, dst):
        self.copied_to.append((src, dst))
        self._events.append('custom')

    @contextlib.contextmanager
    def open(self, path, mode='r'):
        buf = io.StringIO()
        yield buf
        self.written[path] = buf.getvalue()


def _patch_common(monkeypatch, events, distro='rhel'):
    monkeypatch.setattr(tus_contentaccess, 'get_target_major_version', lambda: '9')
    monkeypatch.setattr(tus_contentaccess, 'get_target_version', lambda: '9.6')
    monkeypatch.setattr(tus_contentaccess, 'get_target_distro_id', lambda: distro)
    monkeypatch.setattr(tus_contentaccess.tus_rhui, 'perform_client_swap',
                        lambda *a, **k: events.append('rhui'))
    monkeypatch.setattr(tus_contentaccess.rhsm, 'set_container_mode',
                        lambda ctx: events.append('container_mode'))
    monkeypatch.setattr(tus_contentaccess.rhsm, 'switch_certificate',
                        lambda ctx, info: events.append('switch_cert'))
    monkeypatch.setattr(tus_contentaccess.os.path, 'isdir', lambda p: True)


def test_establish_full_order(monkeypatch):
    events = []
    _patch_common(monkeypatch, events, distro='centos')
    context = FakeContext(events)
    inputs = _Inputs(
        rhui_info=object(),
        rhsm_info=RHSMInfo(existing_product_certificates=[]),
        custom_repofiles=[CustomTargetRepositoryFile(file='/etc/custom.repo')],
    )

    tus_contentaccess.establish(context, inputs)

    # RHUI -> RHSM container-mode -> switch cert -> $stream (centos) -> custom
    assert events == ['rhui', 'container_mode', 'switch_cert', 'custom']
    # $stream variable written for the CentOS target
    assert context.written['/etc/dnf/vars/stream'] == '9-stream\n'
    assert context.copied_to == [('/etc/custom.repo', '/etc/yum.repos.d/custom.repo')]


def test_establish_skips_rhui_without_rhui_info(monkeypatch):
    events = []
    _patch_common(monkeypatch, events, distro='rhel')
    context = FakeContext(events)
    inputs = _Inputs(rhui_info=None, rhsm_info=RHSMInfo(existing_product_certificates=[]))

    tus_contentaccess.establish(context, inputs)

    assert 'rhui' not in events
    assert events == ['container_mode', 'switch_cert']


def test_establish_stream_only_for_centos(monkeypatch):
    events = []
    _patch_common(monkeypatch, events, distro='rhel')
    context = FakeContext(events)
    inputs = _Inputs(rhsm_info=RHSMInfo(existing_product_certificates=[]))

    tus_contentaccess.establish(context, inputs)

    # No $stream file written for a non-CentOS target.
    assert '/etc/dnf/vars/stream' not in context.written


def test_missing_target_cert_propagates(monkeypatch):
    events = []
    _patch_common(monkeypatch, events, distro='rhel')

    def boom(ctx, info):
        raise rhsm.MissingTargetProductCertificate(message='missing cert')

    monkeypatch.setattr(tus_contentaccess.rhsm, 'switch_certificate', boom)
    context = FakeContext(events)
    inputs = _Inputs(rhsm_info=RHSMInfo(existing_product_certificates=[]))

    # establish must NOT catch this - it propagates to the orchestrator (inhibitor #1).
    with pytest.raises(rhsm.MissingTargetProductCertificate):
        tus_contentaccess.establish(context, inputs)
