import os

from leapp.libraries.actor import checkraid
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import MDArray, RAIDInfo, TargetUserSpaceUpgradeTasks


def _mock_path_checks(monkeypatch, files=(), directories=()):
    def isfile(path):
        return path in files

    def isdir(path):
        return path in directories

    monkeypatch.setattr(os.path, 'isfile', isfile)
    monkeypatch.setattr(os.path, 'isdir', isdir)


def _md_arrays(*uuids):
    return [MDArray(uuid=uuid) for uuid in uuids]


def test_md_arrays_with_conf_dir(monkeypatch):
    _mock_path_checks(
        monkeypatch,
        files=('/etc/mdadm.conf',),
        directories=('/etc/mdadm.conf.d',),
    )

    msgs = [RAIDInfo(md_arrays=_md_arrays('aaa:bbb'))]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert api.produce.called == 1
    copy_tasks = [m for m in api.produce.model_instances if isinstance(m, TargetUserSpaceUpgradeTasks)]
    assert len(copy_tasks) == 1
    assert [task.src for task in copy_tasks[0].copy_files] == [
        '/etc/mdadm.conf',
        '/etc/mdadm.conf.d',
    ]


def test_md_arrays_without_conf_dir(monkeypatch):
    _mock_path_checks(monkeypatch, files=('/etc/mdadm.conf',))

    msgs = [RAIDInfo(md_arrays=_md_arrays('aaa:bbb'))]
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

    msgs = [RAIDInfo(md_arrays=_md_arrays('aaa:bbb'))]
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

    msgs = [RAIDInfo(md_arrays=_md_arrays('aaa:bbb'))]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    copy_tasks = [m for m in api.produce.model_instances if isinstance(m, TargetUserSpaceUpgradeTasks)]
    assert not copy_tasks
    assert not api.produce.called


def test_no_raid_info(monkeypatch):
    msgs = []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert not api.produce.called


def test_no_md_arrays(monkeypatch):
    msgs = [RAIDInfo(md_arrays=[])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkraid.process()

    assert not api.produce.called
