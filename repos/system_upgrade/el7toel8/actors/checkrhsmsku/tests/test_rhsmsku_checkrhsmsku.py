from leapp.libraries.actor import checkrhsmsku
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import create_report_mocked
from leapp.libraries.stdlib import api
from leapp.models import RHSMInfo


def test_sku_report_skipped(monkeypatch):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)
    monkeypatch.setattr(api, 'consume', lambda x: (RHSMInfo(attached_skus=[]),))
    monkeypatch.setattr(checkrhsmsku, 'create_report', create_report_mocked())
    checkrhsmsku.process()
    assert not checkrhsmsku.create_report.called


def test_sku_report_has_skus(monkeypatch):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    monkeypatch.setattr(api, 'consume', lambda x: (RHSMInfo(attached_skus=['testing-sku']),))
    monkeypatch.setattr(checkrhsmsku, 'create_report', create_report_mocked())
    checkrhsmsku.process()
    assert not checkrhsmsku.create_report.called


def test_sku_report_has_no_skus(monkeypatch):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    monkeypatch.setattr(api, 'consume', lambda x: (RHSMInfo(attached_skus=[]),))
    monkeypatch.setattr(checkrhsmsku, 'create_report', create_report_mocked())
    checkrhsmsku.process()
    assert checkrhsmsku.create_report.called == 1
    assert checkrhsmsku.create_report.report_fields['title'] == 'The system is not registered or subscribed.'
    assert checkrhsmsku.create_report.report_fields['severity'] == 'high'
    assert 'inhibitor' in checkrhsmsku.create_report.report_fields['groups']
