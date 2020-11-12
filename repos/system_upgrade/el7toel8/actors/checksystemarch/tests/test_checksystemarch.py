from leapp import reporting
from leapp.libraries.actor import checksystemarch
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api


def test_valid_architectures(monkeypatch):
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_ACCEPTED[0]))

    checksystemarch.check_architecture()

    assert reporting.create_report.called == 0


def test_invalid_architecture(monkeypatch):
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='invalid_architecture'))

    checksystemarch.check_architecture()
    assert reporting.create_report.called == 1
    assert 'Unsupported architecture' in reporting.create_report.report_fields['title']
    assert 'Upgrade process is only supported' in reporting.create_report.report_fields['summary']
    assert reporting.create_report.report_fields['severity'] == 'high'
    assert 'inhibitor' in reporting.create_report.report_fields['groups']
