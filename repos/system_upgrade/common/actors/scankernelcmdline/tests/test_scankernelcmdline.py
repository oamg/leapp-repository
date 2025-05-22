import os

import pytest

from leapp.libraries.actor import scankernelcmdline
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdline, KernelCmdlineArg


def test_cmdline_output(monkeypatch):
    mocked_cmd_output = 'BOOT_IMAGE=(hd0,msdos1)/vmlinuz-xxx root=/dev/mapper/guest console=tty0 console=ttyS0,115200 biosdevname=0 net.ifnames=0 crashkernel=auto'

    current_actor = CurrentActorMocked(src_ver='8.10', dst_ver='9.6')
    monkeypatch.setattr(api, 'current_actor', current_actor)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    scankernelcmdline.parse_cmdline_input(mocked_cmd_output)

    expected_params = [KernelCmdlineArg(key=k, value=v) for k, v in [
        ('BOOT_IMAGE', '(hd0,msdos1)/vmlinuz-xxx'),
        ('root', '/dev/mapper/guest'),
        ('console', 'tty0'),
        ('console', 'ttyS0,115200'),
        ('biosdevname', '0'),
        ('net.ifnames', '0'),
        ('crashkernel', 'auto')]]

    expected_output_msg = KernelCmdline(parameters=expected_params)

    assert api.produce.model_instances
    assert expected_output_msg == api.produce.model_instances[0]
