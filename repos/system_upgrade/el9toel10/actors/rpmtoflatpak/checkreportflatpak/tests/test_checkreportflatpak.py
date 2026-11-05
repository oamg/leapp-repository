import pytest

from leapp import reporting
from leapp.libraries.actor import checkreportflatpak
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import FlatpakMigrationPackage, RpmToFlatpakFacts, RpmTransactionTasks


def _make_facts(*rpm_names):
    packages = [
        FlatpakMigrationPackage(
            rpm_name=name,
            preinstall_pkg='redhat-flatpak-preinstall-{}'.format(name),
        )
        for name in rpm_names
    ]
    return RpmToFlatpakFacts(packages=packages)


@pytest.mark.parametrize('facts', [None, _make_facts()])
def test_does_not_report_when_no_packages(monkeypatch, facts):
    msgs = [facts] if facts is not None else []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkreportflatpak, 'skip_rhsm', lambda: False)

    checkreportflatpak.process()

    assert reporting.create_report.called == 0


def test_creates_info_report_and_transaction_tasks_with_rhsm(monkeypatch):
    facts = _make_facts('firefox', 'thunderbird')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkreportflatpak, 'skip_rhsm', lambda: False)

    checkreportflatpak.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.reports[0]
    assert report['title'] == 'Some RPM packages will be migrated to Flatpak'
    assert 'firefox' in report['summary']
    assert 'thunderbird' in report['summary']
    assert reporting.Groups.INHIBITOR not in report['groups']

    tasks = [m for m in api.produce.model_instances if isinstance(m, RpmTransactionTasks)]
    assert len(tasks) == 1
    assert 'flatpak' in tasks[0].to_install
    # flatpak preinstall runs through dbus-run-session, which needs dbus-daemon
    assert 'dbus-tools' in tasks[0].to_install
    assert 'dbus-daemon' in tasks[0].to_install
    assert 'redhat-flatpak-preinstall-firefox' in tasks[0].to_install
    assert 'redhat-flatpak-preinstall-thunderbird' in tasks[0].to_install


def test_creates_report_when_rhsm_not_in_use(monkeypatch):
    facts = _make_facts('firefox')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkreportflatpak, 'skip_rhsm', lambda: True)

    checkreportflatpak.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.reports[0]
    assert report['title'] == 'RPM-to-Flatpak migration is not enabled on this system'
    assert 'firefox' in report['summary']
    # LEAPP_NO_RHSM is an implementation detail and the manual installation
    # instructions belong only to the remediation, not to the summary
    assert 'LEAPP_NO_RHSM' not in report['summary']
    assert 'install the applications manually' not in report['summary']
    # The migration of a few applications must not block the whole upgrade
    assert reporting.Groups.INHIBITOR not in report['groups']
    assert report['severity'] == 'medium'

    tasks = [m for m in api.produce.model_instances if isinstance(m, RpmTransactionTasks)]
    assert not tasks


def test_report_without_rhsm_includes_manual_install_hint(monkeypatch):
    facts = _make_facts('firefox')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkreportflatpak, 'skip_rhsm', lambda: True)

    checkreportflatpak.process()

    report = reporting.create_report.reports[0]
    hints = [rem['context'] for rem in report['detail']['remediations'] if rem['type'] == 'hint']
    assert hints
    assert any('install the applications as Flatpaks manually' in hint for hint in hints)


def test_report_without_rhsm_includes_documentation_link(monkeypatch):
    facts = _make_facts('firefox')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkreportflatpak, 'skip_rhsm', lambda: True)

    checkreportflatpak.process()

    report = reporting.create_report.reports[0]
    ext_links = [e for e in report.get('detail', {}).get('external', [])
                 if 'flatpak' in e.get('url', '')]
    assert ext_links


def test_info_report_includes_documentation_link(monkeypatch):
    facts = _make_facts('firefox')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkreportflatpak, 'skip_rhsm', lambda: False)

    checkreportflatpak.process()

    report = reporting.create_report.reports[0]
    ext_links = [e for e in report.get('detail', {}).get('external', [])
                 if 'flatpak' in e.get('url', '')]
    assert ext_links
