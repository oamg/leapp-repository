import base64
import io
import os
import re
import tarfile
import tempfile

from leapp.libraries.actor import checkvdo
from leapp import reporting
from leapp.libraries.common.testutils import create_report_mocked


def test_nomigration(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
#     monkeypatch.setattr(checkvdo, 'check_service', lambda _: False)
#     monkeypatch.setattr(checkvdo, 'is_file', lambda _: False)
#     monkeypatch.setattr(checkvdo, 'get_tgz64', lambda _: '')

    checkvdo.check_vdo()

    assert reporting.create_report.called == 0


def test_migration(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
#     monkeypatch.setattr(checkvdo, 'check_service', lambda service: service[:-8] in services)
#     monkeypatch.setattr(checkvdo, 'is_file', lambda _: True)
#     monkeypatch.setattr(checkvdo, 'get_tgz64', lambda _: '')

    migrate = set(["a", "b"])
    decision = checkvdo.check_vdo()

    assert reporting.create_report.called == 0
