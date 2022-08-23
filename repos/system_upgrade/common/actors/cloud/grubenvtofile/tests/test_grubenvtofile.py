import pytest

from leapp.libraries.actor import grubenvtofile
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import HybridImage


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
    monkeypatch.setattr(api, 'consume', lambda x: iter([HybridImage()]))
    monkeypatch.setattr(grubenvtofile, 'run', run_mocked())
    grubenvtofile.grubenv_to_file()
    assert grubenvtofile.run.called == 2


def test_fail_grubenv_to_file(monkeypatch):
    monkeypatch.setattr(api, 'consume', lambda x: iter([HybridImage()]))
    monkeypatch.setattr(grubenvtofile, 'run', run_mocked(raise_err=True))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    grubenvtofile.grubenv_to_file()
    assert grubenvtofile.run.called == 1
    assert api.current_logger.warnmsg[0].startswith('Could not unlink')
