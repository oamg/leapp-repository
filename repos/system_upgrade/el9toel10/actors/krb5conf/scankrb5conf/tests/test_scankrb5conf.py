import os

import pytest

from leapp.libraries.actor.scankrb5conf import fetch_outdated_krb5_conf_files

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.parametrize(
    'inp,exp_out',
    [
        ('files/krb5conf_outdated', 'files/krb5conf_outdated'),
        ('files/krb5conf_not_affected', None),
        ('files/krb5conf_not_configured', None),
        ('files/krb5conf_uptodate', None),
    ],
)
def test_fetch_outdated_krb5_conf_files(inp, exp_out):
    file = fetch_outdated_krb5_conf_files(os.path.join(CUR_DIR, inp))
    assert file == os.path.join(CUR_DIR, exp_out)


def test_fetch_outdated_krb5_conf_files():
    msg = fetch_outdated_krb5_conf_files(os.path.join(CUR_DIR, 'files/'))
    assert len(msg.locations) == 1
    assert os.path.join(CUR_DIR, 'files/krb5conf_outdated') in msg.locations
