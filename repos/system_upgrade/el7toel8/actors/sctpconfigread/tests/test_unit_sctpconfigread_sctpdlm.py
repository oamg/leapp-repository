import logging

import pytest
import six

from leapp.libraries.actor import sctpdlm

if six.PY2:
    from mock import mock_open
else:
    from unittest.mock import mock_open


# TODO Confirm with the team the way to mock builtin open
#   and apply this throughout the repo


@pytest.mark.parametrize(
    ('config', 'open_raises', 'exp_return',),
    [
        ('', IOError, False),
        ('', OSError, False),
        ('log_debug=1\npost_join_delay=10', None, False),
        ('log_debug=1\npost_join_delay=10\nprotocol=sctp', None, True),
        ('log_debug=1\npost_join_delay=10\nprotocol=detect', None, True),
        ('log_debug=1\npost_join_delay=10\nprotocol=1', None, True),
        ('log_debug=1\npost_join_delay=10\nprotocol=2', None, True),
        ('log_debug=1\npost_join_delay=10\nprotocol=tcp', None, False),
        ('log_debug=1\npost_join_delay=10', None, False),
    ],
)
def test_check_dlm_cfgfile(config, open_raises, exp_return):
    if open_raises:
        mock_open.side_effect = open_raises
    assert (
        sctpdlm.check_dlm_cfgfile(_open=mock_open(read_data=config))
        == exp_return
    )


@pytest.mark.parametrize(
    ('config', 'open_raises', 'exp_return'),
    [
        ('', IOError, False),
        ('', OSError, False),
        ('DLM_CONTROLD_OPTS="- f 0 -q 0 --protocol=sctp"', None, True),
        ('DLM_CONTROLD_OPTS="- f 0 -q 0 -r detect"', None, True),
        ('DLM_CONTROLD_OPTS="- f 0 -q 0 --protocol tcp"', None, False),
    ],
)
def test_check_dlm_sysconfig(config, open_raises, exp_return):
    if open_raises:
        mock_open.side_effect = open_raises
    assert (
        sctpdlm.check_dlm_sysconfig(_open=mock_open(read_data=config))
        == exp_return
    )


@pytest.mark.parametrize(
    (
        'check_dlm_cfg_file_returns',
        'check_dlm_sysconfig_returns',
        'exp_return',
        'text_in_log',
    ),
    [
        (True, False, True, 'DLM is configured to use SCTP on dlm.conf.'),
        (False, True, True, 'DLM is configured to use SCTP on sysconfig.'),
        (False, False, False, ''),
    ],
)
def test_is_dlm_using_sctp(
    check_dlm_cfg_file_returns,
    check_dlm_sysconfig_returns,
    exp_return,
    text_in_log,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(
        sctpdlm, 'check_dlm_cfgfile', lambda: check_dlm_cfg_file_returns
    )
    monkeypatch.setattr(
        sctpdlm, 'check_dlm_sysconfig', lambda: check_dlm_sysconfig_returns
    )
    with caplog.at_level(logging.DEBUG):
        assert sctpdlm.is_dlm_using_sctp() == exp_return
    if text_in_log:
        assert text_in_log in caplog.text
