import pytest

from leapp import reporting
from leapp.libraries.actor import checkreportflatpak
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FlatpakMigrationPackage, RpmToFlatpakFacts


def _make_facts(*rpm_names):
    packages = [
        FlatpakMigrationPackage(
            rpm_name=name,
            preinstall_pkg='redhat-flatpak-preinstall-{}'.format(name),
        )
        for name in rpm_names
    ]
    return RpmToFlatpakFacts(packages=packages)


@pytest.mark.parametrize('facts,expect_report', [
    (None, False),
    (_make_facts(), False),
    (_make_facts('firefox'), True),
    (_make_facts('firefox', 'thunderbird'), True),
])
def test_process(monkeypatch, facts, expect_report):
    msgs = [facts] if facts is not None else []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkreportflatpak.process()

    assert reporting.create_report.called == (1 if expect_report else 0)


def test_report_contains_package_names(monkeypatch):
    facts = _make_facts('firefox', 'thunderbird')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkreportflatpak.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.reports[0]
    assert 'firefox' in report['title']
    assert 'thunderbird' in report['title']
