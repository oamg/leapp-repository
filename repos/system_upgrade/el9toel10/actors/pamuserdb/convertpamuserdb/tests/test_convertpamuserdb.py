import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import convertpamuserdb
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_convert_db_success(monkeypatch):
    location = os.path.join(CUR_DIR, '/files/db1')

    def run_mocked(cmd, **kwargs):
        assert cmd == ['db_converter', '--src', f'{location}.db', '--dest', f'{location}.gdbm']

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(convertpamuserdb, 'run', run_mocked)
    convertpamuserdb._convert_db(location)
    assert len(api.current_logger.errmsg) == 0


def test_convert_db_failure(monkeypatch):
    location = os.path.join(CUR_DIR, '/files/db1')

    def run_mocked(cmd, **kwargs):
        raise CalledProcessError(
            message='A Leapp Command Error occurred.',
            command=cmd,
            result={'exit_code': 1}
        )

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(convertpamuserdb, 'run', run_mocked)
    with pytest.raises(StopActorExecutionError) as err:
        convertpamuserdb._convert_db(location)
    assert str(err.value) == 'Cannot convert pam_userdb database.'
