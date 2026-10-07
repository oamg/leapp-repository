import pytest

from leapp import reporting
from leapp.libraries.actor import checkosrelease
from leapp.libraries.common.config import version
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import IPUSourceToPossibleTargets
from leapp.utils.report import is_inhibitor


def test_skip_check(monkeypatch):
    monkeypatch.setenv('LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE', '1')
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    assert checkosrelease.skip_check()
    assert reporting.create_report.called == 1
    assert 'Skipped OS release check' in reporting.create_report.report_fields['title']
    assert reporting.create_report.report_fields['severity'] == 'high'


def test_no_skip_check(monkeypatch):
    monkeypatch.delenv('LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE', raising=False)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    assert not checkosrelease.skip_check()
    assert reporting.create_report.called == 0


@pytest.mark.parametrize(
    'src_ver,upgrade_paths,expected_versions',
    [
        (
            '9.4',
            [
                IPUSourceToPossibleTargets(source_version='9.6', target_versions=['10.0']),
                IPUSourceToPossibleTargets(source_version='9.8', target_versions=['10.2']),
                IPUSourceToPossibleTargets(source_version='9.9', target_versions=['10.3']),
            ],
            ('9.6', '9.8', '9.9'),
        ),
        (
            '8.6',
            [
                IPUSourceToPossibleTargets(source_version='8.10', target_versions=['9.6']),
            ],
            ('8.10',),
        ),
        (
            '8',
            [
                IPUSourceToPossibleTargets(source_version='8', target_versions=['9']),
                IPUSourceToPossibleTargets(source_version='8.10', target_versions=['9.6']),
            ],
            ('8', '8.10'),
        ),
        (
            '8.6',
            [
                IPUSourceToPossibleTargets(source_version='8', target_versions=['9']),
                IPUSourceToPossibleTargets(source_version='8.10', target_versions=['9.6']),
            ],
            ('8.10',),
        ),
    ],
)
def test_check_os_version_not_supported(monkeypatch, src_ver, upgrade_paths, expected_versions):
    """Verify the inhibitor is created and its summary lists the supported source versions."""
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(src_ver=src_ver, supported_upgrade_paths=upgrade_paths)
    )
    monkeypatch.setattr(version, 'is_supported_version', lambda: False)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkosrelease.check_os_version()
    assert reporting.create_report.called == 1
    assert 'The installed OS version is not supported' in reporting.create_report.report_fields['title']
    assert is_inhibitor(reporting.create_report.report_fields)
    summary = reporting.create_report.report_fields['summary']
    for ver in expected_versions:
        assert 'RHEL {}'.format(ver) in summary
    assert 'RHEL {}'.format(src_ver) in summary
    external_links = reporting.create_report.report_fields.get('detail', {}).get('external', [])
    assert any(
        link.get('url') == 'https://access.redhat.com/articles/4263361' for link in external_links
    )


def test_check_os_version_saphana_flavour(monkeypatch):
    """Verify the inhibitor summary includes the SAP HANA flavour in the version prefix."""
    upgrade_paths = [
        IPUSourceToPossibleTargets(source_version='9.6', target_versions=['10.0']),
        IPUSourceToPossibleTargets(source_version='9.8', target_versions=['10.2']),
    ]
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(src_ver='9.4', flavour='saphana', supported_upgrade_paths=upgrade_paths)
    )
    monkeypatch.setattr(version, 'is_supported_version', lambda: False)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkosrelease.check_os_version()
    assert reporting.create_report.called == 1
    summary = reporting.create_report.report_fields['summary']
    for ver in ('9.6', '9.8'):
        assert 'RHEL (SAP HANA) {}'.format(ver) in summary
    assert 'RHEL (SAP HANA) 9.4' in summary
    assert is_inhibitor(reporting.create_report.report_fields)


def test_check_os_version_no_external_link_for_non_rhel(monkeypatch):
    """Verify the RHEL KBase external link is not included for non-RHEL distros."""
    upgrade_paths = [
        IPUSourceToPossibleTargets(source_version='9.6', target_versions=['10.0']),
    ]
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(src_ver='9.4', src_distro='centos', supported_upgrade_paths=upgrade_paths)
    )
    monkeypatch.setattr(version, 'is_supported_version', lambda: False)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkosrelease.check_os_version()
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    external_links = reporting.create_report.report_fields.get('detail', {}).get('external', [])
    assert not any(
        link.get('url') == 'https://access.redhat.com/articles/4263361' for link in external_links
    )


def test_check_os_version_supported(monkeypatch):
    monkeypatch.setattr(version, 'is_supported_version', lambda: True)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkosrelease.check_os_version()
    assert reporting.create_report.called == 0
