import logging
import subprocess

import pytest

from leapp.libraries.actor import sctpupdate
from leapp.libraries.stdlib import CalledProcessError

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    (
        'conf_content',
        'exp_new_conf_content',
        'log_should_contain',
        'log_shouldnt_contain',
        'conf_files_exists',
        'should_raise_exc',
        'logger_level',
    ),
    [
        # testing normal behaviour
        (
            'blacklist sctp',
            '#blacklist sctp',
            'Enabled SCTP',
            None,
            True,
            None,
            logging.INFO,
        ),
        # testing if regex works also in case sctp just a part of a string
        (
            'blacklist some-sctp',
            '#blacklist some-sctp',
            'Enabled SCTP',
            None,
            True,
            None,
            logging.INFO,
        ),
        # testing if script skips non sctp lines
        (
            'blacklist tcp',
            'blacklist tcp',
            'Enabled SCTP',
            None,
            True,
            None,
            logging.INFO,
        ),
        # testing if the logger message is empty on warning level
        (
            'blacklist tcp',
            'blacklist tcp',
            '',
            None,
            True,
            None,
            logging.WARNING,
        ),
        # testing if CalledProcessError raised when sed exits with non 0 and
        # logger not emits Enabled SCTP (what we want)
        (
            'blacklist tcp',
            'blacklist tcp',
            None,
            'Enabled SCTP',
            False,
            CalledProcessError,
            logging.INFO,
        ),
    ],
)
def test_enable_sctp(
    conf_content,
    exp_new_conf_content,
    log_should_contain,
    log_shouldnt_contain,
    conf_files_exists,
    should_raise_exc,
    logger_level,
    monkeypatch,
    tmpdir,
    caplog,
    capsys,
):
    def mock_run(args):
        logger.info('Calling run with %r', args)
        res = subprocess.call(args)
        if res != 0:
            raise CalledProcessError(
                message='Sed fails with error code {!r}'.format(res),
                command=args,
                result=res,
            )

    monkeypatch.setattr(sctpupdate, 'run', mock_run)

    sctp_diag_blacklist_conf = tmpdir.join('sctp_diag-blacklist.conf')
    sctp_blacklist_conf = tmpdir.join('sctp-blacklist.conf')
    if conf_files_exists:
        sctp_diag_blacklist_conf.write(conf_content)
        sctp_blacklist_conf.write(conf_content)

    with caplog.at_level(logger_level):
        if not should_raise_exc:
            sctpupdate.enable_sctp(_modprobe_d_path=str(tmpdir))
            with open(str(sctp_blacklist_conf)) as conf:
                assert conf.readlines() == [exp_new_conf_content]
        else:
            with pytest.raises(should_raise_exc):
                sctpupdate.enable_sctp(_modprobe_d_path=str(tmpdir))

    if log_should_contain is not None:
        assert log_should_contain in caplog.text
    if log_shouldnt_contain is not None:
        assert log_shouldnt_contain not in caplog.text
