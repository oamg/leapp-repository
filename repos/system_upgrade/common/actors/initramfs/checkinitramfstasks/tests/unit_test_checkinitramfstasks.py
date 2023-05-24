import os

import pytest

from leapp import reporting
from leapp.libraries.actor import checkinitramfstasks
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DracutModule, KernelModule, TargetInitramfsTasks, UpgradeInitramfsTasks
from leapp.utils.report import is_inhibitor


def gen_UIT(modules):
    if not isinstance(modules, list):
        modules = [modules]
    dracut_modules = [DracutModule(name=i[0], module_path=i[1]) for i in modules]
    kernel_modules = [KernelModule(name=i[0], module_path=i[1]) for i in modules]
    return UpgradeInitramfsTasks(include_dracut_modules=dracut_modules, include_kernel_modules=kernel_modules)


def gen_TIT(modules):
    if not isinstance(modules, list):
        modules = [modules]
    dracut_modules = [DracutModule(name=i[0], module_path=i[1]) for i in modules]
    return TargetInitramfsTasks(include_dracut_modules=dracut_modules)


@pytest.mark.parametrize('expected_res,input_msgs,test_msg_type', [
    (
        {},
        [],
        UpgradeInitramfsTasks,
    ),
    (
        {},
        [gen_UIT([('modA', 'pathA'), ('modB', 'pathB')])],
        UpgradeInitramfsTasks,
    ),
    (
        {},
        [gen_UIT([('modA', 'pathA'), ('modA', 'pathA')])],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {'pathA', 'pathB'}},
        [gen_UIT([('modA', 'pathA'), ('modA', 'pathB')])],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {'pathA', 'pathB'}},
        [gen_UIT(('modA', 'pathA')), gen_UIT(('modA', 'pathB'))],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {'pathA', 'pathB'}},
        [gen_UIT([('modA', 'pathA'), ('modA', 'pathB'), ('modB', 'pathC')])],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {os.path.join(checkinitramfstasks.DRACUT_MOD_DIR, 'modA'), 'pathB'}},
        [gen_UIT([('modA', None), ('modA', 'pathB')])],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {'pathA', 'pathB'}},
        [gen_TIT([('modA', 'pathA'), ('modA', 'pathB')])],
        TargetInitramfsTasks,
    ),
    (
        {},
        [gen_UIT([('modA', 'pathA'), ('modA', 'pathB')])],
        TargetInitramfsTasks,
    ),
])
def test_dracut_conflict_detection(monkeypatch, expected_res, input_msgs, test_msg_type):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=input_msgs))
    res = checkinitramfstasks._detect_modules_conflicts(test_msg_type, 'dracut')
    assert res == expected_res


@pytest.mark.parametrize('expected_res,input_msgs,test_msg_type', [
    (
        {},
        [],
        UpgradeInitramfsTasks,
    ),
    (
        {},
        [gen_UIT([('modA', 'pathA'), ('modB', 'pathB')])],
        UpgradeInitramfsTasks,
    ),
    (
        {},
        [gen_UIT([('modA', 'pathA'), ('modA', 'pathA')])],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {'pathA', 'pathB'}},
        [gen_UIT([('modA', 'pathA'), ('modA', 'pathB')])],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {'pathA', 'pathB'}},
        [gen_UIT(('modA', 'pathA')), gen_UIT(('modA', 'pathB'))],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {'pathA', 'pathB'}},
        [gen_UIT([('modA', 'pathA'), ('modA', 'pathB'), ('modB', 'pathC')])],
        UpgradeInitramfsTasks,
    ),
    (
        {'modA': {'modA (system)', 'pathB'}},
        [gen_UIT([('modA', None), ('modA', 'pathB')])],
        UpgradeInitramfsTasks,
    ),
    (
        {},
        [gen_UIT([('modA', 'pathA'), ('modA', 'pathB')])],
        TargetInitramfsTasks,
    ),
])
def test_kernel_conflict_detection(monkeypatch, expected_res, input_msgs, test_msg_type):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=input_msgs))
    res = checkinitramfstasks._detect_modules_conflicts(test_msg_type, 'kernel')
    assert res == expected_res


def test_report_uit(monkeypatch):
    input_msgs = [gen_UIT([('modA', 'pathA'), ('modA', 'pathB')])]
    sum_msg = "- modA: ['pathA', 'pathB']"
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=input_msgs))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    checkinitramfstasks.process()
    assert reporting.create_report.called
    assert 'upgrade' in reporting.create_report.report_fields['title']
    assert sum_msg in reporting.create_report.report_fields['summary']
    assert is_inhibitor(reporting.create_report.report_fields)


def test_report_tit(monkeypatch):
    input_msgs = [gen_TIT([('modA', 'pathA'), ('modA', 'pathB')])]
    sum_msg = "- modA: ['pathA', 'pathB']"
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=input_msgs))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    checkinitramfstasks.process()
    assert reporting.create_report.called
    assert 'target' in reporting.create_report.report_fields['title']
    assert sum_msg in reporting.create_report.report_fields['summary']
    assert is_inhibitor(reporting.create_report.report_fields)


def test_no_conflict(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    checkinitramfstasks.process()
    assert not reporting.create_report.called
