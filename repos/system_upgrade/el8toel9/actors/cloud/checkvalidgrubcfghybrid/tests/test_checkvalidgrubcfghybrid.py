import pytest

from leapp import reporting
from leapp.libraries.actor import checkvalidgrubcfghybrid
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import HybridImageAzure


@pytest.mark.parametrize('is_hybrid', [True, False])
def test_check_invalid_grubcfg_hybrid(monkeypatch, is_hybrid):

    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    msgs = [HybridImageAzure()] if is_hybrid else []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', msgs=msgs))
    monkeypatch.setattr(api, "produce", produce_mocked())

    checkvalidgrubcfghybrid.process()

    if is_hybrid:
        assert reporting.create_report.called == 1
        assert 'regenerated' in reporting.create_report.report_fields['title']
    else:
        assert reporting.create_report.called == 0
