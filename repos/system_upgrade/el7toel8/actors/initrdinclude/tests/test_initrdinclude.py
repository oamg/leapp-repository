import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import initrdinclude
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.models import InitrdIncludes, InstalledTargetKernelVersion


INCLUDES1 = ["/file1", "/file2", "/dir/ect/ory/file3"]
INCLUDES2 = ["/file4", "/file5"]
KERNEL_VERSION = "4.18.0"


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occured.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'})


class RunMocked(object):
    def __init__(self, raise_err=False):
        self.called = 0
        self.args = []
        self.raise_err = raise_err

    def __call__(self, args):
        self.called += 1
        self.args = args
        if self.raise_err:
            raise_call_error(args)


def test_no_includes(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(initrdinclude, 'run', run_mocked)

    initrdinclude.process()
    assert "No additional files required to add into the initrd." in api.current_logger.dbgmsg
    assert not run_mocked.called


def test_no_kernel_version(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[InitrdIncludes(files=INCLUDES1), InitrdIncludes(files=INCLUDES2)]))
    monkeypatch.setattr(initrdinclude, 'run', run_mocked)

    with pytest.raises(StopActorExecutionError) as e:
        initrdinclude.process()
    assert 'Cannot get version of the installed RHEL-8 kernel' in str(e)
    assert not run_mocked.called


def test_dracut_fail(monkeypatch):
    run_mocked = RunMocked(raise_err=True)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[InitrdIncludes(files=INCLUDES1), InitrdIncludes(files=INCLUDES2),
              InstalledTargetKernelVersion(version=KERNEL_VERSION)]))
    monkeypatch.setattr(initrdinclude, 'run', run_mocked)

    with pytest.raises(StopActorExecutionError) as e:
        initrdinclude.process()
    assert 'Cannot regenerate dracut image' in str(e)
    assert run_mocked.called


def test_flawless(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[InitrdIncludes(files=INCLUDES1), InitrdIncludes(files=INCLUDES2),
              InstalledTargetKernelVersion(version=KERNEL_VERSION)]))
    monkeypatch.setattr(initrdinclude, 'run', run_mocked)

    initrdinclude.process()
    assert run_mocked.called
    for f in INCLUDES1 + INCLUDES2:
        assert (f in arg for arg in run_mocked.args)
