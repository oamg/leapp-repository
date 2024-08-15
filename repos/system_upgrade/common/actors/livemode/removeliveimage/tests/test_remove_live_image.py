import functools
import os

import pytest

from leapp.libraries.actor import remove_live_image as remove_live_image_lib
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import LiveModeArtifacts, LiveModeConfig

_LiveModeConfig = functools.partial(LiveModeConfig, squashfs_fullpath='configured_path')


@pytest.mark.parametrize(
    ('livemode_config', 'squashfs_path', 'should_unlink_be_called'),
    (
        (_LiveModeConfig(is_enabled=True), '/squashfs', True),
        (_LiveModeConfig(is_enabled=True), '/var/lib/leapp/upgrade.img', True),
        (_LiveModeConfig(is_enabled=False), '/var/lib/leapp/upgrade.img', False),
        (None, '/var/lib/leapp/upgrade.img', False),
        (_LiveModeConfig(is_enabled=True), None, False),
    )
)
def test_remove_live_image(monkeypatch, livemode_config, squashfs_path, should_unlink_be_called):
    """ Test whether live-mode image (as found in LiveModeArtifacts) is removed. """

    messages = []
    if livemode_config:
        messages.append(livemode_config)
    if squashfs_path:
        messages.append(LiveModeArtifacts(squashfs_path=squashfs_path))

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=messages))

    def unlink_mock(path):
        if should_unlink_be_called:
            assert path == squashfs_path
            return
        assert False  # If we should not call unlink and we call it then fail the test
    monkeypatch.setattr(os, 'unlink', unlink_mock)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=messages))

    remove_live_image_lib.remove_live_image()
