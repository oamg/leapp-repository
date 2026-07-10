import pytest

from leapp.libraries.actor import checkresumekernelarg
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdline, KernelCmdlineArg, TargetKernelCmdlineArgTasks, UpgradeKernelCmdlineArgTasks

_COMMON_PARAMS = [
    KernelCmdlineArg(key='ro', value=None),
    KernelCmdlineArg(key='root', value='/dev/mapper/rhel-root'),
]


@pytest.mark.parametrize('resume_value', [
    'UUID=010b9c5c-5aca-469b-a852-fdf2fefcf817',
    '/dev/mapper/rhel-swap',
    '/dev/md/swap',
    '/dev/md127',
    '/dev/dm-1',
])
def test_resume_removed_from_upgrade_and_restored_on_target(monkeypatch, resume_value):
    cmdline = KernelCmdline(parameters=_COMMON_PARAMS + [
        KernelCmdlineArg(key='resume', value=resume_value),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[cmdline]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkresumekernelarg.process()

    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert len(upgrade_msgs) == 1
    assert len(upgrade_msgs[0].to_remove) == 1
    assert upgrade_msgs[0].to_remove[0].key == 'resume'
    assert upgrade_msgs[0].to_remove[0].value == resume_value

    target_msgs = [m for m in api.produce.model_instances if isinstance(m, TargetKernelCmdlineArgTasks)]
    assert len(target_msgs) == 1
    assert len(target_msgs[0].to_add) == 1
    assert target_msgs[0].to_add[0].key == 'resume'
    assert target_msgs[0].to_add[0].value == resume_value


def test_multiple_resume_args_all_handled(monkeypatch):
    cmdline = KernelCmdline(parameters=_COMMON_PARAMS + [
        KernelCmdlineArg(key='resume', value='UUID=aaa-bbb'),
        KernelCmdlineArg(key='resume', value='/dev/md127'),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[cmdline]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkresumekernelarg.process()

    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert len(upgrade_msgs) == 1
    removed = {(a.key, a.value) for a in upgrade_msgs[0].to_remove}
    assert removed == {('resume', 'UUID=aaa-bbb'), ('resume', '/dev/md127')}

    target_msgs = [m for m in api.produce.model_instances if isinstance(m, TargetKernelCmdlineArgTasks)]
    assert len(target_msgs) == 1
    added = {(a.key, a.value) for a in target_msgs[0].to_add}
    assert added == {('resume', 'UUID=aaa-bbb'), ('resume', '/dev/md127')}


def test_resume_bare_key_without_value(monkeypatch):
    cmdline = KernelCmdline(parameters=_COMMON_PARAMS + [
        KernelCmdlineArg(key='resume', value=None),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[cmdline]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkresumekernelarg.process()

    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert len(upgrade_msgs) == 1
    assert upgrade_msgs[0].to_remove[0].key == 'resume'
    assert upgrade_msgs[0].to_remove[0].value is None

    target_msgs = [m for m in api.produce.model_instances if isinstance(m, TargetKernelCmdlineArgTasks)]
    assert len(target_msgs) == 1
    assert target_msgs[0].to_add[0].key == 'resume'
    assert target_msgs[0].to_add[0].value is None


def test_no_resume_produces_nothing(monkeypatch):
    cmdline = KernelCmdline(parameters=_COMMON_PARAMS)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[cmdline]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkresumekernelarg.process()

    assert not api.produce.model_instances


def test_no_kernel_cmdline_message_produces_nothing(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkresumekernelarg.process()

    assert not api.produce.model_instances
