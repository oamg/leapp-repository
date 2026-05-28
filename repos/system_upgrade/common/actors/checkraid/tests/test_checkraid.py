import os

from leapp.libraries.actor import checkraid
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import CopyFile, RaidInfo, TargetUserSpaceUpgradeTasks


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
