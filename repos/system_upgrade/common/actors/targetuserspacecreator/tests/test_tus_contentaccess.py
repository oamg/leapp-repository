from unittest import mock

import pytest
from test_tus_mock_utils import make_rhui_info, MockContext, MockInputData

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_contentaccess
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.models import CustomTargetRepositoryFile, RHSMInfo


@pytest.mark.parametrize(('version', 'exp_str'), (
    ('9', '9-stream\n'),
    ('10', '10-stream\n'),
))
@pytest.mark.parametrize('fpath', ('/etc/dnf/vars/stream', '/foo/bar/fname'))
def test_adjust_dnf_stream_variable_writes(version, exp_str, fpath):
    context = MockContext()
    tus_contentaccess._adjust_dnf_stream_variable(context, version, varfile=fpath)
    assert context.written_files == {fpath: exp_str}


@pytest.mark.parametrize('error', [OSError('disk error'), FileNotFoundError('missing')])
def test_adjust_dnf_stream_variable_error(error):
    context = MockContext(open_raises=error)
    with pytest.raises(StopActorExecutionError):
        tus_contentaccess._adjust_dnf_stream_variable(context, '9')
    assert not context.written_files


def test_install_custom_repofiles():
    context = MockContext()
    repofiles = [
        CustomTargetRepositoryFile(file='/home/user/a.repo'),
        CustomTargetRepositoryFile(file='/tmp/sub/b.repo')
    ]
    tus_contentaccess._install_custom_repofiles(context, repofiles)
    assert context.copy_to_calls == [
        ('/home/user/a.repo', '/etc/yum.repos.d/a.repo'),
        ('/tmp/sub/b.repo', '/etc/yum.repos.d/b.repo'),
    ]


def test_install_custom_repofiles_empty():
    context = MockContext()
    tus_contentaccess._install_custom_repofiles(context, [])
    assert not context.copy_to_calls


def _setup_establish(monkeypatch, distro_id, target_version='9.6'):
    context = MockContext()
    rhui_swap_spy = mock.Mock()
    set_container_spy = mock.Mock()
    switch_cert_spy = mock.Mock()

    monkeypatch.setattr(tus_contentaccess.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(
        tus_contentaccess.api,
        'current_actor',
        CurrentActorMocked(dst_ver=target_version, dst_distro=distro_id)
    )

    monkeypatch.setattr(tus_contentaccess.tus_rhui, 'perform_client_swap', rhui_swap_spy)
    monkeypatch.setattr(tus_contentaccess.rhsm, 'set_container_mode', set_container_spy)
    monkeypatch.setattr(tus_contentaccess.rhsm, 'switch_certificate', switch_cert_spy)
    return context, rhui_swap_spy, set_container_spy, switch_cert_spy


@pytest.mark.parametrize('target_version', ('9', '10'))
def test_establish_centos(monkeypatch, target_version):
    context, rhui_swap_spy, set_container_spy, switch_cert_spy = _setup_establish(
        monkeypatch, 'centos', target_version
    )

    repofiles = [CustomTargetRepositoryFile(file='/tmp/custom.repo')]
    inputs = MockInputData(rhui_info=None, rhsm_info=None, custom_repofiles=repofiles, skip_rhsm=True)

    tus_contentaccess.establish(context, inputs)

    rhui_swap_spy.assert_not_called()
    switch_cert_spy.assert_called_once_with(context, None)
    set_container_spy.assert_called_once_with(context)
    assert context.written_files == {'/etc/dnf/vars/stream': f'{target_version}-stream\n'}
    assert context.copy_to_calls == [('/tmp/custom.repo', '/etc/yum.repos.d/custom.repo')]


@pytest.mark.parametrize('target_distro', ('rhel', 'almalinux', 'rocky'))
def test_establish_norhui_norhsm(monkeypatch, target_distro):
    context, rhui_swap_spy, set_container_spy, switch_cert_spy = _setup_establish(monkeypatch, target_distro)

    repofiles = [CustomTargetRepositoryFile(file='/tmp/custom.repo')]
    inputs = MockInputData(rhui_info=None, rhsm_info=None, custom_repofiles=repofiles, skip_rhsm=True)

    tus_contentaccess.establish(context, inputs)

    rhui_swap_spy.assert_not_called()
    switch_cert_spy.assert_called_once_with(context, None)
    set_container_spy.assert_called_once_with(context)
    assert not context.written_files
    assert context.copy_to_calls == [('/tmp/custom.repo', '/etc/yum.repos.d/custom.repo')]


def test_establish_rhel_with_rhsm(monkeypatch):
    context, rhui_swap_spy, set_container_spy, switch_cert_spy = _setup_establish(monkeypatch, 'rhel')

    rhsm_info = RHSMInfo(attached_skus=[], sca_detected=True)
    inputs = MockInputData(rhui_info=None, rhsm_info=rhsm_info, custom_repofiles=[], skip_rhsm=False)

    tus_contentaccess.establish(context, inputs)

    rhui_swap_spy.assert_not_called()
    switch_cert_spy.assert_called_once_with(context, rhsm_info)
    set_container_spy.assert_called_once_with(context)
    assert not context.written_files
    assert not context.copy_to_calls


@pytest.mark.parametrize('target_version', ('9.6', '10.4'))
def test_establish_rhel_with_rhui(monkeypatch, target_version):
    context, rhui_swap_spy, set_container_spy, switch_cert_spy = _setup_establish(
        monkeypatch, 'rhel', target_version
    )

    rhui_info = make_rhui_info()
    inputs = MockInputData(rhui_info=rhui_info, rhsm_info=None, custom_repofiles=[], skip_rhsm=True)

    tus_contentaccess.establish(context, inputs)

    rhui_swap_spy.assert_called_once_with(context, rhui_info, target_version, True)
    switch_cert_spy.assert_called_once_with(context, None)
    set_container_spy.assert_called_once_with(context)
    assert not context.written_files
    assert not context.copy_to_calls
