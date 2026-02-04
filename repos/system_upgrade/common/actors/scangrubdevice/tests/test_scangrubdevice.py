import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import scangrubdevice
from leapp.libraries.common import grub
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import GrubInfo


def test_process_one_dev(monkeypatch):
    def _get_grub_devices_mocked():
        return ['/dev/vda']

    monkeypatch.setattr(grub, 'get_grub_devices', _get_grub_devices_mocked)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scangrubdevice.process()

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    grubinfo = api.produce.model_instances[0]
    assert isinstance(grubinfo, GrubInfo)
    assert grubinfo.orig_devices == ['/dev/vda']
    assert grubinfo.orig_device_name == '/dev/vda'


def test_process_multiple_devs(monkeypatch):
    def _get_grub_devices_mocked():
        return ['/dev/vda', '/dev/vdb']

    monkeypatch.setattr(grub, 'get_grub_devices', _get_grub_devices_mocked)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scangrubdevice.process()

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    grubinfo = api.produce.model_instances[0]
    assert isinstance(grubinfo, GrubInfo)
    assert grubinfo.orig_devices == ['/dev/vda', '/dev/vdb']
    assert grubinfo.orig_device_name is None


def test_process_no_produce_on_s390x(monkeypatch):
    monkeypatch.setattr(
        api, "current_actor", CurrentActorMocked(arch=architecture.ARCH_S390X)
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scangrubdevice.process()

    assert api.produce.called == 0


def test_process_fail_to_get_grubdevs(monkeypatch):

    def _get_grub_devices_mocked():
        raise grub.GRUBDeviceError()

    monkeypatch.setattr(grub, 'get_grub_devices', _get_grub_devices_mocked)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    with pytest.raises(StopActorExecutionError, match='Cannot detect GRUB devices'):
        scangrubdevice.process()
