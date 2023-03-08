import os

import pytest

from leapp.libraries.actor import setetcreleasever
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    PkgManagerInfo,
    RHUIInfo,
    TargetRHUIPostInstallTasks,
    TargetRHUIPreInstallTasks,
    TargetRHUISetupInfo
)

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class mocked_set_releasever(object):
    def __init__(self):
        self.content = None

    def __call__(self, content):
        self.content = content


# def test_set_releasever(monkeypatch):

#     target = '8.0'
#     expected_rel_ver = '8.0'
#     monkeypatch.setattr(setetcreleasever, '_set_releasever', mocked_set_releasever())

#     setetcreleasever.process(target)
#     assert expected_rel_ver == setetcreleasever._set_releasever.content


def test_set_releasever(monkeypatch, current_actor_context):
    preinstall_tasks = TargetRHUIPreInstallTasks()
    postinstall_tasks = TargetRHUIPostInstallTasks()
    setup_info = TargetRHUISetupInfo(preinstall_tasks=preinstall_tasks, postinstall_tasks=postinstall_tasks)
    rhui_info = RHUIInfo(provider='aws',
                         src_client_pkg_names=['rh-amazon-rhui-client'],
                         target_client_pkg_names=['rh-amazon-rhui-client'],
                         target_client_setup_info=setup_info)

    msgs = [rhui_info, PkgManagerInfo(etc_releasever='7.7')]

    expected_rel_ver = '8.0'
    monkeypatch.setattr(setetcreleasever, '_set_releasever', mocked_set_releasever())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=msgs, dst_ver=expected_rel_ver
        )
    )
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    setetcreleasever.process()

    assert expected_rel_ver == setetcreleasever._set_releasever.content
    assert not api.current_logger.dbgmsg


def test_no_set_releasever(monkeypatch, current_actor_context):

    expected_rel_ver = '8.0'
    monkeypatch.setattr(setetcreleasever, '_set_releasever', mocked_set_releasever())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver=expected_rel_ver))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    setetcreleasever.process()

    assert not setetcreleasever._set_releasever.content
    assert api.current_logger.dbgmsg
