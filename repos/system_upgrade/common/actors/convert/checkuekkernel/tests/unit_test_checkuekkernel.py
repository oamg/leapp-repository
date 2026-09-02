import pytest

from leapp import reporting
from leapp.libraries.actor import checkuekkernel
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.utils.report import is_inhibitor

_UEK_KERNELS = [
    '5.15.0-100.96.32.el8uek.x86_64',
    '5.15.0-200.136.2.el9uek.aarch64',
]

_NON_UEK_KERNELS = [
    '4.18.0-513.5.1.el8.x86_64',
    '5.14.0-362.8.1.el9.x86_64',
]


@pytest.mark.parametrize('uname_r', _UEK_KERNELS)
def test_inhibits_on_uek_kernel(monkeypatch, uname_r):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel=uname_r))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkuekkernel.process()

    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert 'UEK' in reporting.create_report.report_fields['title']


@pytest.mark.parametrize('uname_r', _NON_UEK_KERNELS)
def test_no_inhibitor_on_non_uek_kernel(monkeypatch, uname_r):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel=uname_r))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkuekkernel.process()

    assert not reporting.create_report.called
