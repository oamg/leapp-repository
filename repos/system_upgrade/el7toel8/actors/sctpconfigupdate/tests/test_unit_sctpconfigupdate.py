import logging
import subprocess

import pytest

from leapp.libraries.actor import sctpupdate

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    (
        'conf_content',
        'exp_new_conf_content',
        'log_should_contain',
        'log_shouldnt_contain',
    ),
    [
        ('blacklist sctp', '#blacklist sctp', 'Enabled SCTP', ''),
        (
            'blacklist something-else-sctp',
            '#blacklist something-else-sctp',
            'Enabled SCTP',
            '',
        ),
        ('blacklist tcp', 'blacklist tcp', 'Enabled SCTP', ''),
    ],
)
def test_enable_sctp(
    conf_content,
    exp_new_conf_content,
    log_should_contain,
    log_shouldnt_contain,
    monkeypatch,
    tmpdir,
    caplog,
    capsys,
):
    def mock_run(args):
        logger.info('Calling run with %r', args)
        res = subprocess.call(args)
        return {'exit_code': res}

    monkeypatch.setattr(sctpupdate, 'run', mock_run)

    sctp_diag_blacklist_conf = tmpdir.join('sctp_diag-blacklist.conf')
    sctp_blacklist_conf = tmpdir.join('sctp-blacklist.conf')
    sctp_diag_blacklist_conf.write(conf_content)
    sctp_blacklist_conf.write(conf_content)

    with caplog.at_level(logging.DEBUG):
        sctpupdate.enable_sctp(_modprobe_d_path=str(tmpdir))
    with open(str(sctp_blacklist_conf)) as conf:
        assert conf.readlines() == [exp_new_conf_content]
    if log_should_contain:
        assert log_shouldnt_contain in caplog.text
    if log_shouldnt_contain:
        assert log_shouldnt_contain not in caplog.text
