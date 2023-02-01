import os
import shutil
import sys
import tempfile

import distro
import pytest

from leapp.libraries.actor.missinggpgkey import (
    _expand_vars,
    _get_abs_file_path,
    _get_path_to_gpg_certs,
    _get_pubkeys,
    _get_repo_gpgkey_urls,
    _gpg_show_keys,
    _parse_fp_from_gpg,
    _pubkeys_from_rpms
)
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, RepositoryData, RPM, TargetUserSpaceInfo


def is_rhel7():
    return int(distro.major_version()) < 8


def test_gpg_show_keys(current_actor_context, monkeypatch):
    src = '7.9' if is_rhel7() else '8.6'
    current_actor = CurrentActorMocked(src_ver=src)
    monkeypatch.setattr(api, 'current_actor', current_actor)

    # python2 compatibility :/
    dirpath = tempfile.mkdtemp()

    # using GNUPGHOME env should avoid gnupg modifying the system
    os.environ['GNUPGHOME'] = dirpath

    try:
        # non-existing file
        non_existent_path = os.path.join(dirpath, 'nonexistent')
        res = _gpg_show_keys(non_existent_path)
        if is_rhel7():
            err_msg = "gpg: can't open `{}'".format(non_existent_path)
        else:
            err_msg = "gpg: can't open '{}': No such file or directory\n".format(non_existent_path)
        assert not res['stdout']
        assert err_msg in res['stderr']
        assert res['exit_code'] == 2

        fp = _parse_fp_from_gpg(res)
        assert fp == []

        # no gpg data found
        no_key_path = os.path.join(dirpath, "no_key")
        with open(no_key_path, "w") as f:
            f.write('test')

        res = _gpg_show_keys(no_key_path)
        if is_rhel7():
            err_msg = ('gpg: no valid OpenPGP data found.\n'
                       'gpg: processing message failed: Unknown system error\n')
        else:
            err_msg = 'gpg: no valid OpenPGP data found.\n'
        assert not res['stdout']
        assert res['stderr'] == err_msg
        assert res['exit_code'] == 2

        fp = _parse_fp_from_gpg(res)
        assert fp == []

        # with some test data now -- rhel9 release key
        # rhel9_key_path = os.path.join(api.get_common_folder_path('rpm-gpg'), '9')
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        rhel9_key_path = os.path.join(cur_dir, '..', '..', '..', 'files', 'rpm-gpg', '9',
                                      'RPM-GPG-KEY-redhat-release')
        res = _gpg_show_keys(rhel9_key_path)
    finally:
        shutil.rmtree(dirpath)

    if is_rhel7():
        assert len(res['stdout']) == 4
        assert res['stdout'][0] == ('pub:-:4096:1:199E2F91FD431D51:1256212795:::-:'
                                    'Red Hat, Inc. (release key 2) <security@redhat.com>:')
        assert res['stdout'][1] == 'fpr:::::::::567E347AD0044ADE55BA8A5F199E2F91FD431D51:'
        assert res['stdout'][2] == ('pub:-:4096:1:5054E4A45A6340B3:1646863006:::-:'
                                    'Red Hat, Inc. (auxiliary key 3) <security@redhat.com>:')
        assert res['stdout'][3] == 'fpr:::::::::7E4624258C406535D56D6F135054E4A45A6340B3:'
    else:
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
    fp = _parse_fp_from_gpg(res)
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
    fp = _parse_fp_from_gpg(res)
    assert fp == exp


@pytest.mark.parametrize('target, product_type, exp', [
    ('8.6', 'beta', '../../files/rpm-gpg/8beta'),
    ('8.8', 'htb', '../../files/rpm-gpg/8'),
    ('9.0', 'beta', '../../files/rpm-gpg/9beta'),
    ('9.2', 'ga', '../../files/rpm-gpg/9'),
])
def test_get_path_to_gpg_certs(current_actor_context, monkeypatch, target, product_type, exp):
    current_actor = CurrentActorMocked(dst_ver=target,
                                       envars={'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': product_type})
    monkeypatch.setattr(api, 'current_actor', current_actor)

    p = _get_path_to_gpg_certs()
    assert p == exp


@pytest.mark.parametrize('data, exp', [
    ('bare string', 'bare string'),
    ('with dollar$$$', 'with dollar$$$'),
    ('path/with/$basearch/something', 'path/with/x86_64/something'),
    ('path/with/$releasever/something', 'path/with/9/something'),
    ('path/with/$releasever/$basearch', 'path/with/9/x86_64'),
    ('path/with/$releasever/$basearch', 'path/with/9/x86_64'),
])
def test_expand_vars(monkeypatch, data, exp):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.1'))  # x86_64 arch is default
    res = _expand_vars(data)
    assert res == exp


def _get_test_installed_rmps():
    return InstalledRPM(
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


def test_pubkeys_from_rpms():
    installed_rpm = _get_test_installed_rmps()
    assert _pubkeys_from_rpms(installed_rpm) == ['9570ff31']


# @pytest.mark.parametrize('target, product_type, exp', [
#     ('8.6', 'beta', ['F21541EB']),
#     ('8.8', 'htb', ['FD431D51', 'D4082792']),  # ga
#     ('9.0', 'beta', ['F21541EB']),
#     ('9.2', 'ga', ['FD431D51', '5A6340B3']),
# ])
# Def test_get_pubkeys(current_actor_context, monkeypatch, target, product_type, exp):
#     current_actor = CurrentActorMocked(dst_ver=target,
#                                        envars={'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': product_type})
#     monkeypatch.setattr(api, 'current_actor', current_actor)
#     installed_rpm = _get_test_installed_rmps()
#
#     p = _get_pubkeys(installed_rpm)
#     assert '9570ff31' in p
#     for x in exp:
#         assert x in p


@pytest.mark.parametrize('repo, exp', [
    (RepositoryData(repoid='dummy', name='name'), None),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{}'), None),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"1"}'), None),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"0"}'), []),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"no"}'), []),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"False"}'), []),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgkey":"dummy"}'), ["dummy"]),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"1","gpgkey":"dummy"}'),
     ["dummy"]),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgkey":"dummy, another"}'),
     ["dummy", "another"]),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgkey":"dummy\\nanother"}'),
     ["dummy", "another"]),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgkey":"$releasever"}'),
     ["9"]),
])
def test_get_repo_gpgkey_urls(monkeypatch, repo, exp):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.1'))
    keys = _get_repo_gpgkey_urls(repo)
    assert keys == exp


@pytest.mark.parametrize('target_userspace, file_url, exists_in_container, exp', [
    (TargetUserSpaceInfo(path='/', scratch='', mounts=''), 'file:///path/to/key', True, '/path/to/key'),
    (TargetUserSpaceInfo(path='/', scratch='', mounts=''), 'file:///path/to/key', False, '/path/to/key'),
    (TargetUserSpaceInfo(path='/path/to/container/', scratch='', mounts=''), 'file:///path/to/key', True,
     '/path/to/container/path/to/key'),
    (TargetUserSpaceInfo(path='/path/to/container/', scratch='', mounts=''), 'file:///path/to/key', False,
     '/path/to/key'),
    (TargetUserSpaceInfo(path='/path/to/container/', scratch='', mounts=''), 'https://example.com/path/to/key',
     True, 'https://example.com/path/to/key'),
    (TargetUserSpaceInfo(path='/path/to/container/', scratch='', mounts=''), 'https://example.com/path/to/key',
     False, 'https://example.com/path/to/key'),
])
def test_get_abs_file_path(monkeypatch, target_userspace, file_url, exists_in_container, exp):
    def os_path_exists_mocked(path):
        if path == os.path.join(target_userspace.path, file_url[8:]) and exists_in_container:
            return True
        return False

    monkeypatch.setattr('os.path.exists', os_path_exists_mocked)
    path = _get_abs_file_path(target_userspace, file_url)
    assert path == exp
