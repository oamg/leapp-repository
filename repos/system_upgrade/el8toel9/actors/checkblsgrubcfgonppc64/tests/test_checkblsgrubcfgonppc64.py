import pytest

from leapp import reporting
from leapp.libraries.actor import blsgrubcfgonppc64
from leapp.libraries.common import testutils
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DefaultGrub, DefaultGrubInfo, GrubCfgBios


@pytest.mark.parametrize(
    'is_bls,bls_cfg_enabled,is_ppc64', (
        (True, True, True),
        (True, True, False),
        (True, False, True),
        (False, True, False),
        (False, False, False),
    )
)
def test_check_grub_bls_cfg_ppc64(monkeypatch, is_bls, bls_cfg_enabled, is_ppc64):

    grub_cfg_msg = GrubCfgBios(insmod_bls=is_bls)

    bls_cfg_enabled = DefaultGrubInfo(
        default_grub_info=[DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='true')]
    )

    bls_cfg_not_enabled = DefaultGrubInfo(
        default_grub_info=[DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='false')]
    )

    bls_cfg = bls_cfg_enabled if bls_cfg_enabled else bls_cfg_not_enabled

    arch = testutils.architecture.ARCH_PPC64LE if is_ppc64 else testutils.architecture.ARCH_X86_64

    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[grub_cfg_msg, bls_cfg], arch=arch))
    blsgrubcfgonppc64.process()

    if (
        not is_bls and
        is_ppc64 and
        bls_cfg_enabled
    ):
        assert reporting.create_report.called
        assert reporting.create_report.report_fields['title'] == 'TBA'
    else:
        assert not reporting.create_report.called
