from unittest import mock

import pytest
from test_tus_mock_utils import MockNspawnActions

from leapp import reporting
from leapp.libraries.actor import (
    tus_contentaccess,
    tus_inputdata,
    tus_layout,
    tus_targetrepos,
    tus_userspacebuild,
    tus_userspacegen
)
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import create_report_mocked, produce_mocked
from leapp.libraries.stdlib import api


class _MockScratchContainer:
    """Callable returning itself as a context manager yielding a scratch sentinel."""

    def __init__(self, scratch):
        self._scratch = scratch
        self.call_args = None
        self.entered = False
        self.exited = False

    def __call__(self, layout, inputs):
        self.call_args = (layout, inputs)
        return self

    def __enter__(self):
        self.entered = True
        return self._scratch

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exited = True
        return False


@pytest.mark.parametrize(
    ('product_type', 'beta_expected'),
    [
        ('ga', False),
        ('beta', True),
    ]
)
def test_report_missing_target_cert(monkeypatch, product_type, beta_expected):
    created_report = create_report_mocked()
    monkeypatch.setattr(tus_userspacegen.reporting, 'create_report', created_report)
    monkeypatch.setattr(tus_userspacegen, 'get_product_type', mock.Mock(return_value=product_type))

    tus_userspacegen._report_missing_target_cert()

    assert created_report.called == 1
    fields = created_report.report_fields
    assert fields['title'] == 'Missing target system product certificate'
    assert fields['severity'] == reporting.Severity.HIGH
    assert reporting.Groups.SANITY in fields['groups']
    assert reporting.Groups.INHIBITOR in fields['groups']
    assert ('Beta product certificate' in fields['summary']) is beta_expected
    remediations = fields['detail']['remediations']
    assert any('LEAPP_DEVEL_TARGET_RELEASE' in rem.get('context', '') for rem in remediations)


def test_perform_happy_path(monkeypatch):
    inputs = object()
    layout = mock.Mock(userspace_path='/container/el9userspace')
    scratch = object()
    used_repos = object()
    userspace_info = object()
    snapshot = object()

    gather = mock.Mock(return_value=inputs)
    compute = mock.Mock(return_value=layout)
    scratch_container = _MockScratchContainer(scratch)
    establish = mock.Mock()
    select = mock.Mock(return_value=used_repos)
    build = mock.Mock(return_value=userspace_info)
    build_snapshot = mock.Mock(return_value=snapshot)
    produce = produce_mocked()

    monkeypatch.setattr(tus_inputdata, 'gather', gather)
    monkeypatch.setattr(tus_layout, 'compute', compute)
    monkeypatch.setattr(tus_layout, 'scratch_container', scratch_container)
    monkeypatch.setattr(tus_contentaccess, 'establish', establish)
    monkeypatch.setattr(tus_targetrepos, 'select_target_repositories', select)
    monkeypatch.setattr(tus_userspacebuild, 'build', build)
    monkeypatch.setattr(tus_targetrepos, 'build_target_repositories_snapshot', build_snapshot)
    monkeypatch.setattr(tus_userspacegen.mounting, 'NspawnActions', MockNspawnActions)
    monkeypatch.setattr(api, 'produce', produce)

    tus_userspacegen.perform()

    assert scratch_container.call_args == (layout, inputs)
    assert scratch_container.entered
    assert scratch_container.exited
    establish.assert_called_once_with(scratch, inputs)
    select.assert_called_once_with(scratch, inputs)
    build.assert_called_once_with(scratch, layout, inputs, used_repos)
    # The snapshot is parsed from the target userspace (TUS) container, not scratch.
    assert build_snapshot.call_count == 1
    tus_context = build_snapshot.call_args[0][0]
    assert isinstance(tus_context, MockNspawnActions)
    assert tus_context.base_dir == layout.userspace_path
    assert produce.called == 3
    assert produce.model_instances == [userspace_info, used_repos, snapshot]


def test_perform_missing_target_cert_soft_stops(monkeypatch):
    scratch = object()

    inputs = object()
    gather = mock.Mock(return_value=inputs)
    compute = mock.Mock(return_value=object())
    scratch_container = _MockScratchContainer(scratch)
    establish = mock.Mock(side_effect=rhsm.MissingTargetProductCertificate('missing cert'))
    select = mock.Mock()
    build = mock.Mock()
    build_snapshot = mock.Mock()
    report_spy = mock.Mock()
    produce = produce_mocked()

    monkeypatch.setattr(tus_inputdata, 'gather', gather)
    monkeypatch.setattr(tus_layout, 'compute', compute)
    monkeypatch.setattr(tus_layout, 'scratch_container', scratch_container)
    monkeypatch.setattr(tus_contentaccess, 'establish', establish)
    monkeypatch.setattr(tus_targetrepos, 'select_target_repositories', select)
    monkeypatch.setattr(tus_userspacebuild, 'build', build)
    monkeypatch.setattr(tus_targetrepos, 'build_target_repositories_snapshot', build_snapshot)
    monkeypatch.setattr(tus_userspacegen, '_report_missing_target_cert', report_spy)
    monkeypatch.setattr(api, 'produce', produce)

    result = tus_userspacegen.perform()

    assert result is None
    assert scratch_container.entered
    assert scratch_container.exited
    establish.assert_called_once_with(scratch, inputs)
    report_spy.assert_called_once_with()
    select.assert_not_called()
    build.assert_not_called()
    build_snapshot.assert_not_called()
    assert produce.called == 0
