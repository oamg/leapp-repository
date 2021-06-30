import pytest

from leapp.libraries.actor import checknonmountboots390


class CheckNonMountBootS390ReportCreated(Exception):
    pass


@pytest.mark.parametrize(
    'matches_arch,ismount,should_report', (
        (True, True, False),
        (True, False, True),
        (False, True, False),
        (False, False, False),
    )
)
def test_checknonmountboots390_perform_check(monkeypatch, matches_arch, ismount, should_report):
    def _create_report(data):
        raise CheckNonMountBootS390ReportCreated()

    monkeypatch.setattr(checknonmountboots390.architecture, 'matches_architecture', lambda x: matches_arch)
    monkeypatch.setattr(checknonmountboots390.os.path, 'ismount', lambda x: ismount)
    monkeypatch.setattr(checknonmountboots390.reporting, 'create_report', _create_report)

    if should_report:
        with pytest.raises(CheckNonMountBootS390ReportCreated):
            checknonmountboots390.perform_check()
    else:
        checknonmountboots390.perform_check()
