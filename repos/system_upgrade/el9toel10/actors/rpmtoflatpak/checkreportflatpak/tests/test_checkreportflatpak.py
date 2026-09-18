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
    assert report['title'] == 'RPM packages will be migrated to Flatpak'
    assert 'firefox' in report['summary']
    assert 'thunderbird' in report['summary']
    assert reporting.Groups.INHIBITOR not in report['groups']

    tasks = [m for m in api.produce.model_instances if isinstance(m, RpmTransactionTasks)]
    assert len(tasks) == 1
    assert 'flatpak' in tasks[0].to_install
    assert 'redhat-flatpak-preinstall-firefox' in tasks[0].to_install
    assert 'redhat-flatpak-preinstall-thunderbird' in tasks[0].to_install


def test_creates_inhibitor_report_when_rhsm_not_in_use(monkeypatch):
    facts = _make_facts('firefox')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkreportflatpak, 'skip_rhsm', lambda: True)

    checkreportflatpak.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.reports[0]
    assert reporting.Groups.INHIBITOR in report['groups']
    assert 'not supported without RHSM' in report['title']
    assert 'firefox' in report['summary']

    tasks = [m for m in api.produce.model_instances if isinstance(m, RpmTransactionTasks)]
    assert not tasks


def test_inhibitor_report_includes_documentation_link(monkeypatch):
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
