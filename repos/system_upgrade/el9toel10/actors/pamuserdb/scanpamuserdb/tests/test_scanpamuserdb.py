import os

import pytest

from leapp.libraries.actor import scanpamuserdb

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.parametrize(
    "inp,exp_out",
    [
        ("files/pam_userdb_missing", None),
        ("files/pam_userdb_basic", "/tmp/db1"),
        ("files/pam_userdb_complete", "/tmp/db2"),
    ],
)
def test_parse_pam_config_file(inp, exp_out):
    file = scanpamuserdb._parse_pam_config_file(os.path.join(CUR_DIR, inp))
    assert file == exp_out


def test_parse_pam_config_folder():
    msg = scanpamuserdb.parse_pam_config_folder(os.path.join(CUR_DIR, "files/"))
    assert len(msg.locations) == 2
    assert "/tmp/db1" in msg.locations
    assert "/tmp/db2" in msg.locations
