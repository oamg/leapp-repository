import contextlib

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_userspacegen
from leapp.libraries.common import rhsm
from leapp.libraries.stdlib import api
from leapp.models import RepositoriesFactsTarget, TargetUserSpaceInfo, UsedTargetRepositories


def _patch_pipeline(monkeypatch, produced, reports, establish=None):
    userspace_info = TargetUserSpaceInfo(path='/us', scratch='/s', mounts='/m')
    used_repos = UsedTargetRepositories(repos=[])
    snapshot = RepositoriesFactsTarget(repositories=[])

    monkeypatch.setattr(tus_userspacegen.tus_inputdata, 'gather', lambda: 'INPUTS')
    monkeypatch.setattr(tus_userspacegen.tus_layout, 'compute', lambda: 'LAYOUT')

    @contextlib.contextmanager
    def fake_scratch(layout, inputs):
        yield 'SCRATCH'

    monkeypatch.setattr(tus_userspacegen.tus_layout, 'scratch_container', fake_scratch)
    monkeypatch.setattr(tus_userspacegen.tus_contentaccess, 'establish',
                        establish or (lambda ctx, inputs: None))
    monkeypatch.setattr(tus_userspacegen.tus_targetrepos, 'select_target_repositories',
                        lambda ctx, inputs: used_repos)
    monkeypatch.setattr(tus_userspacegen.tus_userspacebuild, 'build',
                        lambda ctx, layout, inputs, used: userspace_info)
    monkeypatch.setattr(tus_userspacegen.tus_targetrepos, 'build_target_repositories_snapshot',
                        lambda ctx: snapshot)
    monkeypatch.setattr(api, 'produce', lambda *msgs: produced.extend(msgs))
    monkeypatch.setattr(tus_userspacegen.reporting, 'create_report',
                        lambda parts: reports.append(parts))
    return userspace_info, used_repos, snapshot


def _parts_of_type(reports, type_name):
    return [p for parts in reports for p in parts if type(p).__name__ == type_name]


def test_perform_happy_path_produces_three_messages_in_order(monkeypatch):
    produced, reports = [], []
    userspace_info, used_repos, snapshot = _patch_pipeline(monkeypatch, produced, reports)

    tus_userspacegen.perform()

    # exactly the three outputs, in the documented order, same objects
    assert produced == [userspace_info, used_repos, snapshot]
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
    titles = [p.value for p in _parts_of_type(reports, 'Title')]
    assert titles == ['Missing target system product certificate']
    # It is an inhibitor and carries the devel-target-release remediation.
    groups = [g for p in _parts_of_type(reports, 'Groups') for g in p.value]
    assert reporting.Groups.INHIBITOR in groups
    assert _parts_of_type(reports, 'Remediation')


def test_perform_missing_cert_non_beta_has_no_beta_note(monkeypatch):
    produced, reports = [], []

    def establish(ctx, inputs):
        raise rhsm.MissingTargetProductCertificate(message='no cert')

    _patch_pipeline(monkeypatch, produced, reports, establish=establish)
    monkeypatch.setattr(tus_userspacegen, 'get_product_type', lambda which: 'ga')

    tus_userspacegen.perform()

    summaries = [p.value for p in _parts_of_type(reports, 'Summary')]
    assert summaries and all('Beta' not in s for s in summaries)


def test_perform_missing_cert_beta_note(monkeypatch):
    produced, reports = [], []

    def establish(ctx, inputs):
        raise rhsm.MissingTargetProductCertificate(message='no cert')

    _patch_pipeline(monkeypatch, produced, reports, establish=establish)
    monkeypatch.setattr(tus_userspacegen, 'get_product_type', lambda which: 'beta')

    tus_userspacegen.perform()

    summaries = [p.value for p in _parts_of_type(reports, 'Summary')]
    assert any('Beta' in s for s in summaries)
