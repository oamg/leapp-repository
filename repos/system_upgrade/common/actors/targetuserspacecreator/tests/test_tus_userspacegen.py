import contextlib

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_userspacegen
from leapp.libraries.common import rhsm
from leapp.libraries.stdlib import api
from leapp.models import RepositoriesFactsTarget, TargetUserSpaceInfo, UsedTargetRepositories


def _patch_pipeline(monkeypatch, produced, reports, establish=None):
    monkeypatch.setattr(tus_userspacegen.tus_inputdata, 'gather', lambda: 'INPUTS')
    monkeypatch.setattr(tus_userspacegen.tus_layout, 'compute', lambda: 'LAYOUT')

    @contextlib.contextmanager
    def fake_scratch(layout, inputs):
        yield 'SCRATCH'

    monkeypatch.setattr(tus_userspacegen.tus_layout, 'scratch_container', fake_scratch)
    monkeypatch.setattr(tus_userspacegen.tus_contentaccess, 'establish',
                        establish or (lambda ctx, inputs: None))
    monkeypatch.setattr(tus_userspacegen.tus_targetrepos, 'select_target_repositories',
                        lambda ctx, inputs: UsedTargetRepositories(repos=[]))
    monkeypatch.setattr(tus_userspacegen.tus_userspacebuild, 'build',
                        lambda ctx, layout, inputs, used: TargetUserSpaceInfo(
                            path='/us', scratch='/s', mounts='/m'))
    monkeypatch.setattr(tus_userspacegen.tus_targetrepos, 'build_target_repositories_snapshot',
                        lambda ctx: RepositoriesFactsTarget(repositories=[]))
    monkeypatch.setattr(api, 'produce', lambda *msgs: produced.extend(msgs))
    monkeypatch.setattr(tus_userspacegen.reporting, 'create_report',
                        lambda parts: reports.append(parts))


def test_perform_happy_path_produces_three_messages(monkeypatch):
    produced, reports = [], []
    _patch_pipeline(monkeypatch, produced, reports)

    tus_userspacegen.perform()

    types = [type(m).__name__ for m in produced]
    assert types == ['TargetUserSpaceInfo', 'UsedTargetRepositories', 'RepositoriesFactsTarget']
    assert reports == []


def test_perform_no_produce_on_gather_hardstop(monkeypatch):
    produced, reports = [], []
    _patch_pipeline(monkeypatch, produced, reports)

    def boom():
        raise StopActorExecutionError(message='bad input')

    monkeypatch.setattr(tus_userspacegen.tus_inputdata, 'gather', boom)

    with pytest.raises(StopActorExecutionError):
        tus_userspacegen.perform()

    assert produced == []


def test_perform_missing_cert_reports_and_no_produce(monkeypatch):
    produced, reports = [], []

    def establish(ctx, inputs):
        raise rhsm.MissingTargetProductCertificate(message='no cert')

    _patch_pipeline(monkeypatch, produced, reports, establish=establish)
    monkeypatch.setattr(tus_userspacegen, 'get_product_type', lambda which: 'ga')

    tus_userspacegen.perform()

    # Inhibitor #1 reported, nothing produced.
    assert produced == []
    assert len(reports) == 1
    titles = [p.value for parts in reports for p in parts if type(p).__name__ == 'Title']
    assert titles == ['Missing target system product certificate']


def test_perform_missing_cert_beta_note(monkeypatch):
    produced, reports = [], []

    def establish(ctx, inputs):
        raise rhsm.MissingTargetProductCertificate(message='no cert')

    _patch_pipeline(monkeypatch, produced, reports, establish=establish)
    monkeypatch.setattr(tus_userspacegen, 'get_product_type', lambda which: 'beta')

    tus_userspacegen.perform()

    summaries = [p.value for parts in reports for p in parts if type(p).__name__ == 'Summary']
    assert any('Beta' in s for s in summaries)
