import pytest

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


class _Recorder:
    """Callable spy recording calls and returning a preset value (or raising)."""

    def __init__(self, return_value=None, raises=None):
        self.return_value = return_value
        self.raises = raises
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.raises is not None:
            raise self.raises
        return self.return_value


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
    monkeypatch.setattr(tus_userspacegen, 'get_product_type', _Recorder(product_type))

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
    layout = object()
    scratch = object()
    used_repos = object()
    userspace_info = object()
    snapshot = object()

    gather = _Recorder(inputs)
    compute = _Recorder(layout)
    scratch_container = _MockScratchContainer(scratch)
    establish = _Recorder()
    select = _Recorder(used_repos)
    build = _Recorder(userspace_info)
    build_snapshot = _Recorder(snapshot)
    produce = produce_mocked()

    monkeypatch.setattr(tus_inputdata, 'gather', gather)
    monkeypatch.setattr(tus_layout, 'compute', compute)
    monkeypatch.setattr(tus_layout, 'scratch_container', scratch_container)
    monkeypatch.setattr(tus_contentaccess, 'establish', establish)
    monkeypatch.setattr(tus_targetrepos, 'select_target_repositories', select)
    monkeypatch.setattr(tus_userspacebuild, 'build', build)
    monkeypatch.setattr(tus_targetrepos, 'build_target_repositories_snapshot', build_snapshot)
    monkeypatch.setattr(api, 'produce', produce)

    tus_userspacegen.perform()

    assert scratch_container.call_args == (layout, inputs)
    assert scratch_container.entered
    assert scratch_container.exited
    assert establish.calls == [((scratch, inputs), {})]
    assert select.calls == [((scratch, inputs), {})]
    assert build.calls == [((scratch, layout, inputs, used_repos), {})]
    assert build_snapshot.calls == [((scratch,), {})]
    assert produce.called == 3
    assert produce.model_instances == [userspace_info, used_repos, snapshot]


def test_perform_missing_target_cert_soft_stops(monkeypatch):
    scratch = object()

    inputs = object()
    gather = _Recorder(inputs)
    compute = _Recorder(object())
    scratch_container = _MockScratchContainer(scratch)
    establish = _Recorder(raises=rhsm.MissingTargetProductCertificate('missing cert'))
    select = _Recorder()
    build = _Recorder()
    build_snapshot = _Recorder()
    report_spy = _Recorder()
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
    assert establish.calls == [((scratch, inputs), {})]
    assert report_spy.calls == [((), {})]
    assert not select.calls
    assert not build.calls
    assert not build_snapshot.calls
    assert produce.called == 0
