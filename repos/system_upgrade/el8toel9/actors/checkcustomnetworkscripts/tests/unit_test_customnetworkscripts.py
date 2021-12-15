import os

from leapp import reporting
from leapp.libraries.actor import customnetworkscripts
from leapp.libraries.common import testutils


def test_customnetworkscripts_exists(monkeypatch):
    monkeypatch.setattr(os.path, "isfile", lambda dummy: True)
    monkeypatch.setattr(reporting, "create_report", testutils.create_report_mocked())
    customnetworkscripts.process()
    assert reporting.create_report.called


def test_customnetworkscripts_not_found(monkeypatch):
    monkeypatch.setattr(os.path, "isfile", lambda dummy: False)
    monkeypatch.setattr(reporting, 'create_report', testutils.create_report_mocked())
    customnetworkscripts.process()
    assert not reporting.create_report.called
