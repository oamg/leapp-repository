import os

from leapp.libraries.actor import checkraid
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    KernelCmdline,
    KernelCmdlineArg,
    RaidInfo,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeKernelCmdlineArgTasks,
)


def _mock_path_checks(monkeypatch, files=(), directories=()):
    def isfile(path):
        return path in files

    def isdir(path):
        return path in directories

    monkeypatch.setattr(os.path, 'isfile', isfile)
    monkeypatch.setattr(os.path, 'isdir', isdir)


def test_mdraid_used_with_conf_dir(monkeypatch):
    _mock_path_checks(
        monkeypatch,
        files=('/etc/mdadm.conf',),
        directories=('/etc/mdadm.conf.d',),
    )

    msgs = [RaidInfo(mdraid_used=True)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    produced = api.produce.model_instances[0]
    assert isinstance(produced, TargetUserSpaceUpgradeTasks)
    assert [task.src for task in produced.copy_files] == [
        '/etc/mdadm.conf',
        '/etc/mdadm.conf.d',
    ]


def test_mdraid_used_without_conf_dir(monkeypatch):
    _mock_path_checks(monkeypatch, files=('/etc/mdadm.conf',))

    msgs = [RaidInfo(mdraid_used=True)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert api.produce.called == 1
    produced = api.produce.model_instances[0]
    assert [task.src for task in produced.copy_files] == ['/etc/mdadm.conf']


def test_mdraid_used_alternative_mdadm_conf(monkeypatch):
    _mock_path_checks(
        monkeypatch,
        files=('/etc/mdadm/mdadm.conf',),
        directories=('/etc/mdadm/mdadm.conf.d',),
    )

    msgs = [RaidInfo(mdraid_used=True)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert api.produce.called == 1
    produced = api.produce.model_instances[0]
    assert [task.src for task in produced.copy_files] == [
        '/etc/mdadm/mdadm.conf',
        '/etc/mdadm/mdadm.conf.d',
    ]


def test_mdraid_used_no_config_paths(monkeypatch):
    _mock_path_checks(monkeypatch)

    msgs = [RaidInfo(mdraid_used=True)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert not api.produce.called


def test_no_raid_info(monkeypatch):
    msgs = []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert not api.produce.called


def test_mdraid_not_used(monkeypatch):
    msgs = [RaidInfo(mdraid_used=False)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert not api.produce.called


def test_rdmd_uuid_args_removed_from_upgrade_cmdline(monkeypatch):
    cmdline = KernelCmdline(parameters=[
        KernelCmdlineArg(key='root', value='/dev/mapper/rhel-root'),
        KernelCmdlineArg(key='rd.md.uuid', value='aaa:bbb'),
        KernelCmdlineArg(key='rd.md.uuid', value='ccc:ddd'),
        KernelCmdlineArg(key='ro', value=None),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[cmdline]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid._emit_rdmd_undesired_for_upgrade_cmdline()

    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert len(upgrade_msgs) == 1

    removed_keys_values = {(arg.key, arg.value) for arg in upgrade_msgs[0].to_remove}
    assert removed_keys_values == {
        ('rd.md.uuid', 'aaa:bbb'),
        ('rd.md.uuid', 'ccc:ddd'),
    }

    target_msgs = [m for m in api.produce.model_instances if isinstance(m, TargetKernelCmdlineArgTasks)]
    assert len(target_msgs) == 1

    readded_keys_values = {(arg.key, arg.value) for arg in target_msgs[0].to_add}
    assert readded_keys_values == {
        ('rd.md.uuid', 'aaa:bbb'),
        ('rd.md.uuid', 'ccc:ddd'),
    }


def test_no_rdmd_uuid_no_message(monkeypatch):
    cmdline = KernelCmdline(parameters=[
        KernelCmdlineArg(key='root', value='/dev/mapper/rhel-root'),
        KernelCmdlineArg(key='ro', value=None),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[cmdline]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid._emit_rdmd_undesired_for_upgrade_cmdline()

    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert not upgrade_msgs
    target_msgs = [m for m in api.produce.model_instances if isinstance(m, TargetKernelCmdlineArgTasks)]
    assert not target_msgs


def test_mdraid_used_with_rdmd_uuid_on_cmdline(monkeypatch):
    _mock_path_checks(monkeypatch, files=('/etc/mdadm.conf',))

    cmdline = KernelCmdline(parameters=[
        KernelCmdlineArg(key='rd.md.uuid', value='aaa:bbb'),
    ])
    msgs = [RaidInfo(mdraid_used=True), cmdline]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert api.produce.called == 3
    produced_types = {type(m) for m in api.produce.model_instances}
    assert produced_types == {TargetUserSpaceUpgradeTasks, UpgradeKernelCmdlineArgTasks, TargetKernelCmdlineArgTasks}
