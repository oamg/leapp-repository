import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import mock_configs
from leapp.models import FirmwareFacts, GrubInfo
from leapp.reporting import Report

NO_GRUB = 'Leapp could not identify where GRUB2 core is located'


def test_actor_update_grub(current_actor_context):
    current_actor_context.feed(FirmwareFacts(firmware='bios'))
    current_actor_context.feed(GrubInfo(orig_device_name='/dev/vda'))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(Report)


def test_actor_no_grub_device(current_actor_context):
    current_actor_context.feed(FirmwareFacts(firmware='bios'))
    current_actor_context.feed(GrubInfo())
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(Report)
    assert current_actor_context.consume(Report)[0].report['title'].startswith(NO_GRUB)


def test_actor_with_efi(current_actor_context):
    current_actor_context.feed(FirmwareFacts(firmware='efi'))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert not current_actor_context.consume(Report)


def test_s390x(current_actor_context):
    current_actor_context.feed(FirmwareFacts(firmware='bios'))
    current_actor_context.feed(GrubInfo(orig_device_name='/dev/vda'))
    current_actor_context.run(config_model=mock_configs.CONFIG_S390X)
    assert not current_actor_context.consume(Report)
