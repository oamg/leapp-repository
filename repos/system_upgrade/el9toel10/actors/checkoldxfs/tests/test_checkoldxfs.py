import pytest

from leapp import reporting
from leapp.libraries.actor import checkarmbootloader
from leapp.libraries.common.config.architecture import ARCH_ARM64, ARCH_SUPPORTED
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize("arch", [arch for arch in ARCH_SUPPORTED if not arch == ARCH_ARM64])
def test_not_x86_64_passes(monkeypatch, arch):
    """
    Test no report is generated on an architecture different from ARM
    """

    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=arch))

    checkarmbootloader.process()

    assert 'Architecture not ARM.' in api.current_logger.infomsg[0]
    assert not reporting.create_report.called


@pytest.mark.parametrize("target_version", ["9.2", "9.4"])
def test_valid_path(monkeypatch, target_version):
    """
    Test no report is generated on a supported path
    """

    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(arch=ARCH_ARM64, src_ver='8.10', dst_ver=target_version)
    )

    checkarmbootloader.process()

    assert 'Upgrade on ARM architecture on a compatible path' in api.current_logger.infomsg[0]
    assert not reporting.create_report.called


def test_invalid_path(monkeypatch):
    """
    Test report is generated on a invalid upgrade path
    """

    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(arch=ARCH_ARM64, src_ver='8.10', dst_ver='9.5')
    )

    checkarmbootloader.process()

    produced_title = reporting.create_report.report_fields.get('title')
    produced_summary = reporting.create_report.report_fields.get('summary')

    assert reporting.create_report.called == 1
    assert 'not possible for ARM machines' in produced_title
    assert 'Due to the incompatibility' in produced_summary
    assert reporting.create_report.report_fields['severity'] == reporting.Severity.HIGH
    assert is_inhibitor(reporting.create_report.report_fields)
