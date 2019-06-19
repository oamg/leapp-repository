import mock
import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import reporting, requirearchver
from leapp.libraries.common.testutils import report_generic_mocked


def test_get_os_release_info(monkeypatch):
    expected = {
        'ANSI_COLOR': '0;31',
        'BUG_REPORT_URL': 'https://bugzilla.redhat.com/',
        'CPE_NAME': 'cpe:/o:redhat:enterprise_linux:7.6:GA:server',
        'HOME_URL': 'https://www.redhat.com/',
        'ID': 'rhel',
        'ID_LIKE': 'fedora',
        'NAME': 'Red Hat Enterprise Linux Server',
        'PRETTY_NAME': 'Red Hat Enterprise Linux',
        'REDHAT_BUGZILLA_PRODUCT': 'Red Hat Enterprise Linux 7',
        'REDHAT_BUGZILLA_PRODUCT_VERSION': '7.6',
        'REDHAT_SUPPORT_PRODUCT': 'Red Hat Enterprise Linux',
        'REDHAT_SUPPORT_PRODUCT_VERSION': '7.6',
        'VARIANT': 'Server',
        'VARIANT_ID': 'server',
        'VERSION': '7.6 (Maipo)',
        'VERSION_ID': '7.6'
    }
    assert expected == requirearchver.get_os_release_info('tests/files/os-release')

    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    assert not requirearchver.get_os_release_info('tests/files/non-existent-file')
    assert reporting.report_generic.called == 1
    assert 'inhibitor' in reporting.report_generic.report_fields['flags']


def test_require_src_minor_version_pass(monkeypatch):
    monkeypatch.setattr(requirearchver, 'get_os_release_info', lambda _unused: {'VERSION_ID': '7.6'})
    assert requirearchver.require_src_minor_version([5, 6, 7]) is None

    assert requirearchver.require_src_minor_version(['5+']) is None

    assert requirearchver.require_src_minor_version(['5>']) is None

    assert requirearchver.require_src_minor_version(['7-']) is None

    assert requirearchver.require_src_minor_version(['7<']) is None


def test_require_src_minor_version_fail(monkeypatch):
    monkeypatch.setattr(requirearchver, 'get_os_release_info', lambda _unused: {'VERSION_ID': '7.6'})
    with pytest.raises(StopActorExecution):
        requirearchver.require_src_minor_version([5])

    with pytest.raises(StopActorExecution):
        requirearchver.require_src_minor_version(['6+'])

    with pytest.raises(StopActorExecution):
        requirearchver.require_src_minor_version(['6-'])

    with pytest.raises(StopActorExecution):
        requirearchver.require_src_minor_version(['5+', '4-'])


def test_require_src_minor_version_wrong_args():
    with pytest.raises(TypeError):
        requirearchver.require_src_minor_version('5')

    with pytest.raises(TypeError):
        requirearchver.require_src_minor_version(['5?'])

    with pytest.raises(TypeError):
        requirearchver.require_src_minor_version(['5+', 4])


def test_require_arch_pass():
    arch = 'some_arch'
    with mock.patch('platform.machine', return_value=arch):
        assert requirearchver.require_arch([arch, 'other_arch']) is None


def test_require_arch_fail():
    with mock.patch('platform.machine', return_value='some_arch'):
        with pytest.raises(StopActorExecution):
            requirearchver.require_arch(['other_arch'])


def test_require_arch_wrong_args():
    with pytest.raises(TypeError):
        requirearchver.require_arch('some_arch')
