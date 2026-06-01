import pytest

from leapp import reporting
from leapp.libraries.actor import checkvarrunsymlink
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FileInfo, TrackedFilesInfoSource
from leapp.utils.report import is_inhibitor


def _msg_varrun(real_path):
    return TrackedFilesInfoSource(files=[
        FileInfo(path='/var/run', exists=True, is_modified=False, real_path=real_path)
    ])


@pytest.mark.parametrize('real_path, should_inhibit', [
    ('/run', False),
    ('/var/run', True),
    ('/tmp/foo', True),
])
def test_check_var_run_symlink(monkeypatch, real_path, should_inhibit):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[_msg_varrun(real_path)]
    ))

    checkvarrunsymlink.process()

    assert bool(reporting.create_report.called) == should_inhibit
    if should_inhibit:
        assert is_inhibitor(reporting.create_report.report_fields)


def test_check_var_run_missing_message(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))

    checkvarrunsymlink.process()

    assert not reporting.create_report.called
