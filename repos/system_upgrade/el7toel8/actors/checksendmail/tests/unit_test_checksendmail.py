import os

import pytest
from six import text_type

from leapp.libraries.actor import checksendmail


@pytest.mark.parametrize('test_input,migrate', [
    ('IPv6:::1\n', True),
    ('IPv6:0:0:0:0:0:0:0:1\n', False),
])
def test_check_migration(tmpdir, monkeypatch, test_input, migrate):
    test_cfg_path = text_type(tmpdir)
    test_cfg_file = os.path.join(test_cfg_path, 'sendmail.cf')
    with open(test_cfg_file, 'w') as file_out:
        file_out.write(test_input)
    monkeypatch.setattr(checksendmail, 'SendmailConfDir', test_cfg_path)
    files = checksendmail.check_files_for_compressed_ipv6()
    if migrate:
        assert files == [test_cfg_file]
    else:
        assert files == []
