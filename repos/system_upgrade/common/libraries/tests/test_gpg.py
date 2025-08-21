import os
import shutil
import tempfile

import distro
import pytest

from leapp.libraries.common import gpg
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import GpgKey, InstalledRPM, RPM


@pytest.mark.parametrize('target, product_type, distro, exp', [
    ('9.0', 'beta', 'rhel', '../../files/distro/rhel/rpm-gpg/9beta'),
    ('9.2', 'ga', 'rhel', '../../files/distro/rhel/rpm-gpg/9'),
    ('10.0', 'ga', 'rhel', '../../files/distro/rhel/rpm-gpg/10'),
    ('10', 'ga', 'centos', '../../files/distro/centos/rpm-gpg/10'),
    ('9.6', 'ga', 'almalinux', '../../files/distro/almalinux/rpm-gpg/9'),
    ('10.0', 'ga', 'almalinux', '../../files/distro/almalinux/rpm-gpg/10'),
])
def test_get_path_to_gpg_certs(monkeypatch, target, product_type, distro, exp):
    current_actor = CurrentActorMocked(dst_ver=target, release_id=distro,
                                       envars={'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': product_type})
    monkeypatch.setattr(api, 'current_actor', current_actor)

    p = gpg.get_path_to_gpg_certs()
    assert p == exp


@pytest.mark.skipif(distro.id() not in ("rhel", "centos"), reason="Requires RHEL or CentOS for valid results.")
def test_gpg_show_keys(loaded_leapp_repository, monkeypatch):
    current_actor = CurrentActorMocked(src_ver='8.10', release_id='rhel')
    monkeypatch.setattr(api, 'current_actor', current_actor)

    # python2 compatibility :/
    dirpath = tempfile.mkdtemp()

    # using GNUPGHOME env should avoid gnupg modifying the system
    os.environ['GNUPGHOME'] = dirpath

    try:
        # non-existing file
        non_existent_path = os.path.join(dirpath, 'nonexistent')
        res = gpg._gpg_show_keys(non_existent_path)
        assert not res['stdout']
        err_msg = "gpg: can't open '{}': No such file or directory\n".format(non_existent_path)
        assert err_msg in res['stderr']
        assert res['exit_code'] == 2

        fp = gpg._parse_fp_from_gpg(res)
        assert fp == []

        # no gpg data found
        no_key_path = os.path.join(dirpath, "no_key")
        with open(no_key_path, "w") as f:
            f.write('test')

        res = gpg._gpg_show_keys(no_key_path)
        assert not res['stdout']
        assert res['stderr'] == 'gpg: no valid OpenPGP data found.\n'
        assert res['exit_code'] == 2

        fp = gpg._parse_fp_from_gpg(res)
        assert fp == []

        # with some test data now -- rhel9 release key
        # rhel9_key_path = os.path.join(api.get_common_folder_path('rpm-gpg'), '9')
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        rhel9_key_path = os.path.join(cur_dir, '..', '..', 'files',
                                      'distro', 'rhel', 'rpm-gpg', '9',
                                      'RPM-GPG-KEY-redhat-release')
        res = gpg._gpg_show_keys(rhel9_key_path)
    finally:
        shutil.rmtree(dirpath)

    assert len(res['stdout']) == 6
    assert res['stdout'][0] == 'pub:-:4096:1:199E2F91FD431D51:1256212795:::-:::scSC::::::23::0:'
    assert res['stdout'][1] == 'fpr:::::::::567E347AD0044ADE55BA8A5F199E2F91FD431D51:'
    assert res['stdout'][2] == ('uid:-::::1256212795::DC1CAEC7997B3575101BB0FCAAC6191792660D8F::'
                                'Red Hat, Inc. (release key 2) <security@redhat.com>::::::::::0:')
    assert res['stdout'][3] == 'pub:-:4096:1:5054E4A45A6340B3:1646863006:::-:::scSC::::::23::0:'
    assert res['stdout'][4] == 'fpr:::::::::7E4624258C406535D56D6F135054E4A45A6340B3:'
    assert res['stdout'][5] == ('uid:-::::1646863006::DA7F68E3872D6E7BDCE05225E7EB5F3ACDD9699F::'
                                'Red Hat, Inc. (auxiliary key 3) <security@redhat.com>::::::::::0:')

    err = '{}/trustdb.gpg: trustdb created'.format(dirpath)
    assert err in res['stderr']
    assert res['exit_code'] == 0

    # now, parse the output too
    fp = gpg._parse_fp_from_gpg(res)
    assert fp == ['fd431d51', '5a6340b3']


@pytest.mark.parametrize('res, exp', [
    ({'exit_code': 2, 'stdout': '', 'stderr': ''}, []),
    ({'exit_code': 2, 'stdout': '', 'stderr': 'bash: gpg2: command not found...'}, []),
    ({'exit_code': 0, 'stdout': 'Some other output', 'stderr': ''}, []),
    ({'exit_code': 0, 'stdout': ['Some other output', 'other line'], 'stderr': ''}, []),
    ({'exit_code': 0, 'stdout': ['pub:-:4096:1:199E2F91FD431D:'], 'stderr': ''}, []),
    ({'exit_code': 0, 'stdout': ['pub:-:4096:1:5054E4A45A6340B3:1..'], 'stderr': ''}, ['5a6340b3']),
])
def test_parse_fp_from_gpg(res, exp):
    fp = gpg._parse_fp_from_gpg(res)
    assert fp == exp


def test_pubkeys_from_rpms():
    installed_rpms = InstalledRPM(
        items=[
            RPM(name='gpg-pubkey',
                version='9570ff31',
                release='5e3006fb',
                epoch='0',
                packager='Fedora (33) <fedora-33-primary@fedoraproject.org>',
                arch='noarch',
                pgpsig=''),
            RPM(name='rpm',
                version='4.17.1',
                release='3.fc35',
                epoch='0',
                packager='Fedora Project',
                arch='x86_64',
                pgpsig='RSA/SHA256, Tue 02 Aug 2022 03:12:43 PM CEST, Key ID db4639719867c58f'),
        ],
    )
    assert gpg.get_pubkeys_from_rpms(installed_rpms) == [GpgKey(fingerprint='9570ff31', rpmdb=True)]
