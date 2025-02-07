import os

import pytest

from leapp.libraries.actor.scankrb5conf import fetch_outdated_krb5_conf_files

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.parametrize(
    'inp,exp_out',
    [
        (['files/krb5conf_outdated'], ['files/krb5conf_outdated']),
        (['files/krb5conf_not_affected'], []),
        (['files/krb5conf_not_configured'], []),
        (['files/krb5conf_uptodate'], []),
        (['files'], ['files/krb5conf_outdated']),
    ],
)
def test_fetch_outdated_krb5_conf_files_with_files(inp, exp_out):
    msg = fetch_outdated_krb5_conf_files([os.path.join(CUR_DIR, i) for i in inp])
    assert len(msg.locations) == len(exp_out)
    assert set(msg.locations) == set(os.path.join(CUR_DIR, o) for o in exp_out)
