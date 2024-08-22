import pytest

from leapp.libraries.actor import convertgrubenvtofile
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import ConvertGrubenvTask


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


class run_mocked(object):
    def __init__(self, raise_err=False):
        self.called = 0
        self.args = []
        self.raise_err = raise_err

    def __call__(self, *args):
        self.called += 1
        self.args.append(args)
        if self.raise_err:
            raise_call_error(args)


def test_grubenv_to_file(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', msgs=[ConvertGrubenvTask()]))
    monkeypatch.setattr(convertgrubenvtofile, 'run', run_mocked(raise_err=False))
    convertgrubenvtofile.process()
    assert convertgrubenvtofile.run.called == 2


def test_no_grubenv_to_file(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', msgs=[]))
    monkeypatch.setattr(convertgrubenvtofile, 'run', run_mocked(raise_err=False))
    convertgrubenvtofile.process()
    assert convertgrubenvtofile.run.called == 0


def test_fail_grubenv_to_file(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', msgs=[ConvertGrubenvTask()]))
    monkeypatch.setattr(convertgrubenvtofile, 'run', run_mocked(raise_err=True))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    convertgrubenvtofile.grubenv_to_file()

    assert convertgrubenvtofile.run.called == 1
    assert api.current_logger.warnmsg[0].startswith('Could not unlink')
