import os

from leapp.libraries.actor import checkraid
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import MDArray, RaidInfo, TargetUserSpaceUpgradeTasks, UpgradeKernelCmdlineArgTasks


def _mock_path_checks(monkeypatch, files=(), directories=()):
    def isfile(path):
        return path in files

    def isdir(path):
        return path in directories

    monkeypatch.setattr(os.path, 'isfile', isfile)
    monkeypatch.setattr(os.path, 'isdir', isdir)


def _md_arrays(*uuids):
    return [MDArray(UUID=uuid) for uuid in uuids]


def test_md_arrays_with_conf_dir(monkeypatch):
    _mock_path_checks(
        monkeypatch,
        files=('/etc/mdadm.conf',),
        directories=('/etc/mdadm.conf.d',),
    )

    msgs = [RaidInfo(md_arrays=_md_arrays('aaa:bbb'))]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert api.produce.called == 2
    copy_tasks = [m for m in api.produce.model_instances if isinstance(m, TargetUserSpaceUpgradeTasks)]
    assert len(copy_tasks) == 1
    assert [task.src for task in copy_tasks[0].copy_files] == [
        '/etc/mdadm.conf',
        '/etc/mdadm.conf.d',
    ]


def test_md_arrays_without_conf_dir(monkeypatch):
    _mock_path_checks(monkeypatch, files=('/etc/mdadm.conf',))

    msgs = [RaidInfo(md_arrays=_md_arrays('aaa:bbb'))]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    copy_tasks = [m for m in api.produce.model_instances if isinstance(m, TargetUserSpaceUpgradeTasks)]
    assert len(copy_tasks) == 1
    assert [task.src for task in copy_tasks[0].copy_files] == ['/etc/mdadm.conf']


def test_md_arrays_alternative_mdadm_conf(monkeypatch):
    _mock_path_checks(
        monkeypatch,
        files=('/etc/mdadm/mdadm.conf',),
        directories=('/etc/mdadm/mdadm.conf.d',),
    )

    msgs = [RaidInfo(md_arrays=_md_arrays('aaa:bbb'))]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    copy_tasks = [m for m in api.produce.model_instances if isinstance(m, TargetUserSpaceUpgradeTasks)]
    assert len(copy_tasks) == 1
    assert [task.src for task in copy_tasks[0].copy_files] == [
        '/etc/mdadm/mdadm.conf',
        '/etc/mdadm/mdadm.conf.d',
    ]


def test_md_arrays_no_config_paths(monkeypatch):
    _mock_path_checks(monkeypatch)

    msgs = [RaidInfo(md_arrays=_md_arrays('aaa:bbb'))]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    copy_tasks = [m for m in api.produce.model_instances if isinstance(m, TargetUserSpaceUpgradeTasks)]
    assert not copy_tasks
    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert len(upgrade_msgs) == 1


def test_no_raid_info(monkeypatch):
    msgs = []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert not api.produce.called


def test_no_md_arrays(monkeypatch):
    msgs = [RaidInfo(md_arrays=[])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert not api.produce.called


def test_md_arrays_emit_rdmd_uuid(monkeypatch):
    _mock_path_checks(monkeypatch, files=('/etc/mdadm.conf',))

    msgs = [RaidInfo(md_arrays=_md_arrays('aaa:bbb', 'ccc:ddd'))]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert len(upgrade_msgs) == 1

    added_keys_values = {(arg.key, arg.value) for arg in upgrade_msgs[0].to_add}
    assert added_keys_values == {
        ('rd.md.uuid', 'aaa:bbb'),
        ('rd.md.uuid', 'ccc:ddd'),
    }
