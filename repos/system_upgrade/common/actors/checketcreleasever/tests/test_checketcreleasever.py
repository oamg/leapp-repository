import os

import pytest

from leapp import reporting
from leapp.libraries.actor import checketcreleasever
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    PkgManagerInfo,
    Report,
    RHUIInfo,
    TargetRHUIPostInstallTasks,
    TargetRHUIPreInstallTasks,
    TargetRHUISetupInfo
)


@pytest.mark.parametrize('exists', [True, False])
def test_etc_releasever(monkeypatch, exists):
    pkg_mgr_msg = [PkgManagerInfo(etc_releasever='7.7')] if exists else []
    expected_rel_ver = '6.10'

    mocked_report = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=pkg_mgr_msg, dst_ver=expected_rel_ver
        )
    )
    monkeypatch.setattr(reporting, 'create_report', mocked_report)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    checketcreleasever.process()

    if exists:
        assert reporting.create_report.called == 1
        assert expected_rel_ver in mocked_report.report_fields['summary']
        assert not api.current_logger.dbgmsg
    else:
        assert not reporting.create_report.called
        assert api.current_logger.dbgmsg


def test_etc_releasever_empty(monkeypatch):
    pkg_mgr_msg = [PkgManagerInfo(etc_releasever=None)]
    expected_rel_ver = '6.10'

    mocked_report = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=pkg_mgr_msg, dst_ver=expected_rel_ver
        )
    )
    monkeypatch.setattr(reporting, 'create_report', mocked_report)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    checketcreleasever.process()

    assert not reporting.create_report.called
    assert api.current_logger.dbgmsg


def mk_rhui_info():
    preinstall_tasks = TargetRHUIPreInstallTasks()
    postinstall_tasks = TargetRHUIPostInstallTasks()
    setup_info = TargetRHUISetupInfo(preinstall_tasks=preinstall_tasks, postinstall_tasks=postinstall_tasks)
    rhui_info = RHUIInfo(provider='aws',
                         src_client_pkg_names=['rh-amazon-rhui-client'],
                         target_client_pkg_names=['rh-amazon-rhui-client'],
                         target_client_setup_info=setup_info)
    return rhui_info


@pytest.mark.parametrize('is_rhui', [True, False])
def test_etc_releasever_rhui(monkeypatch, is_rhui):
    if is_rhui:
        rhui_msg = [mk_rhui_info()]
    else:
        rhui_msg = []

    expected_rel_ver = '6.10'

    mocked_report = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=rhui_msg, dst_ver=expected_rel_ver
        )
    )
    monkeypatch.setattr(reporting, 'create_report', mocked_report)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    checketcreleasever.process()

    if is_rhui:
        assert reporting.create_report.called == 1
        assert expected_rel_ver in mocked_report.report_fields['summary']
        assert not api.current_logger.dbgmsg
    else:
        assert not reporting.create_report.called
        assert api.current_logger.dbgmsg


def test_etc_releasever_neither(monkeypatch):
    mocked_report = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', mocked_report)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    checketcreleasever.process()

    assert not reporting.create_report.called
    assert api.current_logger.dbgmsg


def test_etc_releasever_both(monkeypatch):
    rhui_info = mk_rhui_info()

    msgs = [rhui_info, PkgManagerInfo(etc_releasever='7.7')]
    expected_rel_ver = '6.10'

    mocked_report = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=msgs, dst_ver=expected_rel_ver
        )
    )
    monkeypatch.setattr(reporting, 'create_report', mocked_report)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    checketcreleasever.process()

    assert reporting.create_report.called == 1
    assert expected_rel_ver in mocked_report.report_fields['summary']
    assert not api.current_logger.dbgmsg
