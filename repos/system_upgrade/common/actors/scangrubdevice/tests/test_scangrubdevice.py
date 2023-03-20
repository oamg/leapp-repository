from leapp.libraries.common import grub
from leapp.libraries.common.config import mock_configs
from leapp.models import GrubInfo


def _get_grub_devices_mocked():
    return ['/dev/vda', '/dev/vdb']


def test_actor_scan_grub_device(current_actor_context, monkeypatch):
    monkeypatch.setattr(grub, 'get_grub_devices', _get_grub_devices_mocked)
    current_actor_context.run(config_model=mock_configs.CONFIG)
    info = current_actor_context.consume(GrubInfo)
    assert info and info[0].orig_devices == ['/dev/vda', '/dev/vdb']
    assert len(info) == 1, 'Expected just one GrubInfo message'
    assert not info[0].orig_device_name


def test_actor_scan_grub_device_one(current_actor_context, monkeypatch):

    def _get_grub_devices_mocked():
        return ['/dev/vda']

    monkeypatch.setattr(grub, 'get_grub_devices', _get_grub_devices_mocked)
    current_actor_context.run(config_model=mock_configs.CONFIG)
    info = current_actor_context.consume(GrubInfo)
    assert info and info[0].orig_devices == ['/dev/vda']
    assert len(info) == 1, 'Expected just one GrubInfo message'
    assert info[0].orig_device_name == '/dev/vda'


def test_actor_scan_grub_device_s390x(current_actor_context, monkeypatch):
    monkeypatch.setattr(grub, 'get_grub_devices', _get_grub_devices_mocked)
    current_actor_context.run(config_model=mock_configs.CONFIG_S390X)
    assert not current_actor_context.consume(GrubInfo)
