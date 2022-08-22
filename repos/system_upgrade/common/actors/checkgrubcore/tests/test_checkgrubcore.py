from leapp.libraries.common.config import mock_configs
from leapp.models import FirmwareFacts, GrubDevice, UpdateGrub
from leapp.reporting import Report


def test_actor_update_grub(current_actor_context):
    current_actor_context.feed(FirmwareFacts(firmware='bios'))
    current_actor_context.feed(GrubDevice(grub_device='/dev/vda'))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(Report)
    assert current_actor_context.consume(UpdateGrub)
    assert current_actor_context.consume(UpdateGrub)[0].grub_device == '/dev/vda'


def test_actor_no_grub_device(current_actor_context):
    current_actor_context.feed(FirmwareFacts(firmware='bios'))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(Report)
    assert not current_actor_context.consume(UpdateGrub)


def test_actor_with_efi(current_actor_context):
    current_actor_context.feed(FirmwareFacts(firmware='efi'))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert not current_actor_context.consume(Report)
    assert not current_actor_context.consume(UpdateGrub)


def test_s390x(current_actor_context):
    current_actor_context.feed(FirmwareFacts(firmware='bios'))
    current_actor_context.feed(GrubDevice(grub_device='/dev/vda'))
    current_actor_context.run(config_model=mock_configs.CONFIG_S390X)
    assert not current_actor_context.consume(Report)
    assert not current_actor_context.consume(UpdateGrub)
