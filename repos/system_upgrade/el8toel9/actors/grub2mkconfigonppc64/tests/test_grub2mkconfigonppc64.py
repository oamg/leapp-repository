import os
from io import StringIO

import pytest

from leapp.libraries.actor import grub2mkconfigonppc64
from leapp.libraries.common import testutils
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DefaultGrub, DefaultGrubInfo, FirmwareFacts

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class MockedRun(object):
    def __init__(self):
        self.commands = []

    def __call__(self, cmd, *args, **kwargs):
        self.commands.append(cmd)
        return {}


@pytest.mark.parametrize('cmd_issued', [True, False])
def test_run_grub2mkconfig(monkeypatch, cmd_issued):

    grub2_cfg_bls_excerpt = (
        'fi'
        'insmod blscfg'
        'blscfg'
        '### END /etc/grub.d/10_linux ###'
    )

    grub2_cfg_non_bls_excerpt = (
        '### BEGIN /etc/grub.d/10_linux ###'
        'menuentry "Red Hat Enterprise Linux Server (3.10.0-1160.45.1.el7.x86_64) 7.9 (Maipo)"'
    )

    class _mock_open(object):
        def __init__(self, path, mode):
            input_ = grub2_cfg_non_bls_excerpt if cmd_issued else grub2_cfg_bls_excerpt
            self._fp = StringIO(input_)

        def __enter__(self):
            return self._fp

        def __exit__(self, *args, **kwargs):
            return None

    bls_cfg_enabled = DefaultGrubInfo(
        default_grub_info=[DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='true')]
    )

    bls_cfg_not_enabled = DefaultGrubInfo(
        default_grub_info=[DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='false')]
    )

    bls_cfg = bls_cfg_enabled if cmd_issued else bls_cfg_not_enabled

    arch = testutils.architecture.ARCH_PPC64LE if cmd_issued else testutils.architecture.ARCH_X86_64

    ppc64le_bare = FirmwareFacts(firmware='bios', ppc64le_opal=True)
    ppc64le_virt = FirmwareFacts(firmware='bios', ppc64le_opal=False)

    opal = ppc64le_virt if cmd_issued else ppc64le_bare

    mocked_run = MockedRun()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[bls_cfg, opal], arch=arch))
    monkeypatch.setattr(grub2mkconfigonppc64, 'run', mocked_run)
    monkeypatch.setattr(grub2mkconfigonppc64, 'open', _mock_open, False)
    grub2mkconfigonppc64.process()
    if cmd_issued:
        assert mocked_run.commands == [['grub2-mkconfig', '-o', '/boot/grub2/grub.cfg']]
    else:
        assert not mocked_run.commands
