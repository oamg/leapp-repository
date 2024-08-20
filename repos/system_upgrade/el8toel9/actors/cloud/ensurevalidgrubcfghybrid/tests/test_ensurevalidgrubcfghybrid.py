import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import ensurevalidgrubcfghybrid
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import HybridImage

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


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


def test_not_hybrid_image(monkeypatch):
    """
    Skip when system is not a hybrid.
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(ensurevalidgrubcfghybrid, 'run', run_mocked(raise_err=False))

    ensurevalidgrubcfghybrid.process()

    assert api.current_logger.infomsg[0].startswith('System is not a hybrid image')
    assert ensurevalidgrubcfghybrid.run.called == 0


@pytest.mark.parametrize("is_invalid", [True, False])
def test_is_grubcfg_valid(monkeypatch, is_invalid):

    grubcfg_filename = ('invalid' if is_invalid else 'valid') + '_grub.cfg'
    grubcfg_filepath = os.path.join(CUR_DIR, 'files', grubcfg_filename)
    with open(grubcfg_filepath, 'r') as fin:
        grubcfg = fin.read()

    assert ensurevalidgrubcfghybrid._is_grubcfg_invalid(grubcfg) == is_invalid


def test_valid_grubcfg(monkeypatch):
    """
    Test valid configuration does not trigger grub2-mkconfig
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[HybridImage()]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(ensurevalidgrubcfghybrid, 'run', run_mocked(raise_err=False))

    grubcfg_filepath = os.path.join(CUR_DIR, 'files', 'valid_grub.cfg')
    with open(grubcfg_filepath, 'r') as fin:
        grubcfg = fin.read()

    monkeypatch.setattr(ensurevalidgrubcfghybrid, '_read_grubcfg', lambda: grubcfg)

    ensurevalidgrubcfghybrid.process()

    assert ensurevalidgrubcfghybrid.run.called == 0


def test_invalid_grubcfg(monkeypatch):
    """
    Test invalid configuration triggers grub2-mkconfig
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[HybridImage()]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(ensurevalidgrubcfghybrid, 'run', run_mocked(raise_err=False))

    grubcfg_filepath = os.path.join(CUR_DIR, 'files', 'invalid_grub.cfg')
    with open(grubcfg_filepath, 'r') as fin:
        grubcfg = fin.read()

    monkeypatch.setattr(ensurevalidgrubcfghybrid, '_read_grubcfg', lambda: grubcfg)

    ensurevalidgrubcfghybrid.process()

    assert ensurevalidgrubcfghybrid.run.called == 1
    assert any(msg.startswith('Regenerating') for msg in api.current_logger.infomsg)


def test_run_error(monkeypatch):
    """
    Test invalid configuration triggers grub2-mkconfig
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[HybridImage()]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(ensurevalidgrubcfghybrid, 'run', run_mocked(raise_err=True))

    grubcfg_filepath = os.path.join(CUR_DIR, 'files', 'invalid_grub.cfg')
    with open(grubcfg_filepath, 'r') as fin:
        grubcfg = fin.read()

    monkeypatch.setattr(ensurevalidgrubcfghybrid, '_read_grubcfg', lambda: grubcfg)

    with pytest.raises(StopActorExecutionError):
        ensurevalidgrubcfghybrid.process()

        assert ensurevalidgrubcfghybrid.run.called == 1
        assert any(
            msg.startswith('Could not regenerate')
            for msg in api.current_logger.err
        )
