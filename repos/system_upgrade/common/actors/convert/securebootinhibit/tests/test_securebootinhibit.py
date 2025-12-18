import pytest

from leapp import reporting
from leapp.libraries.actor import securebootinhibit
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts


@pytest.mark.parametrize(
    'ff,is_conversion,should_inhibit', [
        # conversion, secureboot enabled = inhibit
        (
            FirmwareFacts(firmware='efi', ppc64le_opal=None, secureboot_enabled=True),
            True,
            True
        ),
        (
            FirmwareFacts(firmware='efi', ppc64le_opal=None, secureboot_enabled=True),
            False,
            False
        ),
        # bios is ok
        (
            FirmwareFacts(firmware='bios', ppc64le_opal=None, secureboot_enabled=False),
            False,
            False
        ),
        # bios is ok during conversion too
        (
            FirmwareFacts(firmware='bios', ppc64le_opal=None, secureboot_enabled=False),
            True,
            False
        ),
        (
            FirmwareFacts(firmware='efi', ppc64le_opal=None, secureboot_enabled=False),
            True,
            False
        ),
        (
            FirmwareFacts(firmware='efi', ppc64le_opal=None, secureboot_enabled=False),
            False,
            False
        ),
    ]
)
def test_process(monkeypatch, ff, is_conversion, should_inhibit):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[ff]))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(securebootinhibit, "is_conversion", lambda: is_conversion)

    securebootinhibit.process()

    if should_inhibit:
        assert reporting.create_report.called == 1
        assert reporting.Groups.INHIBITOR in reporting.create_report.report_fields['groups']
    else:
        assert not reporting.create_report.called
