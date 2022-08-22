import logging
from functools import partial

import pytest

from leapp.libraries.actor import sctpdlm, sctplib
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.models import ActiveKernelModule, ActiveKernelModulesFacts

FILENAME_SCTP = 'sctp'
FILENAME_NO_SCTP = 'no_sctp'
SRC_VER = '7.6'

logger = logging.getLogger(__name__)


def test_anyfile(tmpdir):
    file1 = tmpdir.join('file1')
    file2 = tmpdir.join('file2')
    file1.write('I am not empty')
    file2.write('And me either')

    assert sctplib.anyfile((str(file1),))
    assert sctplib.anyfile((str(file1), str(tmpdir)))
    assert not sctplib.anyfile((str(tmpdir),))
    assert not sctplib.anyfile(('Iam not exist',))


def test_is_module_loaded(monkeypatch):
    monkeypatch.setattr(
        sctplib.api,
        'current_actor',
        CurrentActorMocked(
            src_ver=SRC_VER,
            msgs=[
                ActiveKernelModulesFacts(
                    kernel_modules=[
                        ActiveKernelModule(
                            filename=FILENAME_SCTP, parameters=()
                        ),
                    ]
                ),
            ],
        ),
    )
    assert sctplib.is_module_loaded(FILENAME_SCTP)
    assert not sctplib.is_module_loaded('not exists filename')


@pytest.mark.parametrize(
    (
        'actor',
        'exp_return',
        'anyfile_returns',
        'check_dlm_cfgfile_returns',
        'check_dlm_sysconfig_returns',
        'text_in_log',
    ),
    [
        # test if module name is sctp
        (
            CurrentActorMocked(
                src_ver=SRC_VER,
                msgs=[
                    ActiveKernelModulesFacts(
                        kernel_modules=[
                            ActiveKernelModule(
                                filename=FILENAME_SCTP, parameters=()
                            )
                        ]
                    )
                ],
            ),
            True,
            False,
            False,
            False,
            '',
        ),
        # test if module name is different, but one of lksctp is present
        (
            CurrentActorMocked(
                src_ver=SRC_VER,
                msgs=[
                    ActiveKernelModulesFacts(
                        kernel_modules=[
                            ActiveKernelModule(
                                filename=FILENAME_NO_SCTP, parameters=()
                            )
                        ]
                    )
                ],
            ),
            True,
            True,
            False,
            False,
            'lksctp files',
        ),
        # test if check_dlm_cfgfile is True
        (
            CurrentActorMocked(
                src_ver=SRC_VER,
                msgs=[
                    ActiveKernelModulesFacts(
                        kernel_modules=[
                            ActiveKernelModule(
                                filename=FILENAME_NO_SCTP, parameters=()
                            )
                        ]
                    )
                ],
            ),
            True,
            False,
            True,
            False,
            'dlm.conf',
        ),
        # test if check_dlm_sysconfig is True
        (
            CurrentActorMocked(
                src_ver=SRC_VER,
                msgs=[
                    ActiveKernelModulesFacts(
                        kernel_modules=[
                            ActiveKernelModule(
                                filename=FILENAME_NO_SCTP, parameters=()
                            )
                        ]
                    )
                ],
            ),
            True,
            False,
            False,
            True,
            'sysconfig',
        ),
    ],
)
def test_is_sctp_used(
    actor,
    exp_return,
    anyfile_returns,
    check_dlm_cfgfile_returns,
    check_dlm_sysconfig_returns,
    text_in_log,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(sctplib.api, 'current_actor', actor)
    monkeypatch.setattr(sctplib, 'anyfile', lambda arg: anyfile_returns)
    monkeypatch.setattr(
        sctpdlm, 'check_dlm_cfgfile', lambda: check_dlm_cfgfile_returns
    )
    monkeypatch.setattr(
        sctpdlm, 'check_dlm_sysconfig', lambda: check_dlm_sysconfig_returns
    )
    with caplog.at_level(logging.DEBUG):
        assert sctplib.is_sctp_used() == exp_return
    if text_in_log:
        assert text_in_log in caplog.text


class RunMocked(object):
    """Simple mock class for leapp.libraries.stdlib.run."""

    def __init__(self, exc_type=None):
        """if exc_type provided, then it will be raised on
        instance call.

        :type exc_type: None or BaseException
        """
        self.exc_type = exc_type

    def __call__(self, *args, **kwargs):
        if self.exc_type:
            logger.info('Mocked `run` raising %r', self.exc_type)
            raise self.exc_type()
        logger.info('Mocked `run` passed without exp.')


@pytest.mark.parametrize(
    ('run_fails', 'exp_return', 'text_in_log'),
    [
        (True, False, 'Nothing regarding SCTP was found on journal.'),
        (False, True, 'Found logs regarding SCTP on journal.'),
    ],
)
def test_was_sctp_used(
    monkeypatch, caplog, run_fails, exp_return, text_in_log
):
    monkeypatch.setattr(
        sctplib,
        'run',
        RunMocked(
            exc_type=partial(
                sctplib.CalledProcessError, 'message', 'command', 'result'
            )
            if run_fails
            else None
        ),
    )
    with caplog.at_level(logging.DEBUG):
        assert sctplib.was_sctp_used() == exp_return
    if text_in_log:
        assert text_in_log in caplog.text


@pytest.mark.parametrize(
    (
        'is_sctp_used_returns',
        'was_sctp_used_returns',
        'exp_return',
        'text_in_log',
    ),
    [
        (True, False, True, 'SCTP is being used.'),
        (False, True, True, 'SCTP was used.'),
        (False, False, False, 'SCTP is not being used and neither wanted.'),
    ],
)
def test_is_sctp_wanted(
    is_sctp_used_returns,
    was_sctp_used_returns,
    exp_return,
    text_in_log,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(sctplib, 'is_sctp_used', lambda: is_sctp_used_returns)
    monkeypatch.setattr(
        sctplib, 'was_sctp_used', lambda: was_sctp_used_returns
    )
    with caplog.at_level(logging.DEBUG):
        assert sctplib.is_sctp_wanted() == exp_return
    if text_in_log:
        assert text_in_log in caplog.text
