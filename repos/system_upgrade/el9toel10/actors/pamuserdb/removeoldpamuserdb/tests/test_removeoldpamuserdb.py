import os

from leapp.libraries.actor import removeoldpamuserdb
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_remove_db_success(monkeypatch):
    location = os.path.join(CUR_DIR, '/files/db1')

    def run_mocked(cmd, **kwargs):
        assert cmd == ['rm', '-f', f'{location}.db']

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(removeoldpamuserdb, 'run', run_mocked)
    removeoldpamuserdb._remove_db(location)
    assert len(api.current_logger.errmsg) == 0


def test_remove_db_failure(monkeypatch):
    location = os.path.join(CUR_DIR, '/files/db1')

    def run_mocked(cmd, **kwargs):
        raise CalledProcessError(
            message='A Leapp Command Error occurred.',
            command=cmd,
            result={'exit_code': 1}
        )

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(removeoldpamuserdb, 'run', run_mocked)
    removeoldpamuserdb._remove_db(location)
    assert (
        'Failed to remove /files/db1.db'
        not in api.current_logger.errmsg
    )
