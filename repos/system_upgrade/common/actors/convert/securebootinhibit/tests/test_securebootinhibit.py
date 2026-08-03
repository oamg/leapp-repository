import pytest

from leapp import reporting
from leapp.libraries.actor import securebootinhibit
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts


def _ff(firmware='efi', secureboot_enabled=None, efi_vars_accessible=None):
    return FirmwareFacts(
        firmware=firmware,
        ppc64le_opal=None,
        secureboot_enabled=secureboot_enabled,
        efi_vars_accessible=efi_vars_accessible,
    )


class _CurrentActorWithDialog(CurrentActorMocked):
    def __init__(self, *args, **kwargs):
        self._sb_answer = kwargs.pop('sb_answer', None)
        super().__init__(*args, **kwargs)

    def get_sb_answer(self):
        return self._sb_answer


@pytest.mark.parametrize(
    'ff,is_conversion,should_inhibit', [
        # SB enabled + conversion = inhibit
        (_ff(secureboot_enabled=True, efi_vars_accessible=True), True, True),
        # SB enabled + no conversion = no report
        (_ff(secureboot_enabled=True, efi_vars_accessible=True), False, False),
        # SB disabled + conversion = no report
        (_ff(secureboot_enabled=False, efi_vars_accessible=True), True, False),
        # SB disabled + no conversion = no report
        (_ff(secureboot_enabled=False, efi_vars_accessible=True), False, False),
        # BIOS + conversion = no report
        (_ff(firmware='bios', secureboot_enabled=False), True, False),
        # BIOS + no conversion = no report
        (_ff(firmware='bios', secureboot_enabled=False), False, False),
    ]
)
def test_process_definitive_sb_state(monkeypatch, ff, is_conversion, should_inhibit):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[ff]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(securebootinhibit, 'is_conversion', lambda: is_conversion)

    securebootinhibit.process()

    if should_inhibit:
        assert reporting.create_report.called == 1
        assert reporting.Groups.INHIBITOR in reporting.create_report.report_fields['groups']
    else:
        assert not reporting.create_report.called


def test_sb_none_efi_vars_accessible(monkeypatch):
    """HW does not support Secure Boot -- efi_vars work, sb is None."""
    ff = _ff(secureboot_enabled=None, efi_vars_accessible=True)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[ff]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(securebootinhibit, 'is_conversion', lambda: True)

    securebootinhibit.process()

    assert not reporting.create_report.called


@pytest.mark.parametrize(
    'sb_answer,should_inhibit', [
        (False, False),
        (True, True),
        (None, True),
    ]
)
def test_sb_none_efi_vars_inaccessible_dialog(monkeypatch, sb_answer, should_inhibit):
    """EFI vars inaccessible -- dialog determines outcome."""
    ff = _ff(secureboot_enabled=None, efi_vars_accessible=False)
    monkeypatch.setattr(
        api, 'current_actor',
        _CurrentActorWithDialog(sb_answer=sb_answer, msgs=[ff]),
    )
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(securebootinhibit, 'is_conversion', lambda: True)

    securebootinhibit.process()

    if should_inhibit:
        assert reporting.create_report.called == 1
        assert reporting.Groups.INHIBITOR in reporting.create_report.report_fields['groups']
    else:
        assert not reporting.create_report.called


def test_sb_none_efi_vars_none_dialog(monkeypatch):
    """efi_vars_accessible is None (mokutil missing) -- falls to dialog, no answer = inhibit."""
    ff = _ff(secureboot_enabled=None, efi_vars_accessible=None)
    monkeypatch.setattr(
        api, 'current_actor',
        _CurrentActorWithDialog(sb_answer=None, msgs=[ff]),
    )
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(securebootinhibit, 'is_conversion', lambda: True)

    securebootinhibit.process()

    assert reporting.create_report.called == 1
    assert reporting.Groups.INHIBITOR in reporting.create_report.report_fields['groups']
