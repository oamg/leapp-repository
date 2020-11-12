from leapp import reporting
from leapp.libraries.actor import checkmemory
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import MemoryInfo


def test_check_memory_low(monkeypatch):
    minimum_req_error = []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    minimum_req_error = checkmemory._check_memory(MemoryInfo(mem_total=1024))
    assert minimum_req_error


def test_check_memory_high(monkeypatch):
    minimum_req_error = []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    minimum_req_error = checkmemory._check_memory(MemoryInfo(mem_total=16273492))
    assert not minimum_req_error


def test_report(monkeypatch):
    title_msg = 'Minimum memory requirements for RHEL 8 are not met'
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'consume', lambda x: iter([MemoryInfo(mem_total=129)]))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    checkmemory.process()
    assert reporting.create_report.called
    assert title_msg == reporting.create_report.report_fields['title']
    assert reporting.Groups.INHIBITOR in reporting.create_report.report_fields['groups']
