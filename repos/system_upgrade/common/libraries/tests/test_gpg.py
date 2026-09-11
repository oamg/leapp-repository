import os
import shutil
import tempfile

import distro
import pytest

from leapp.libraries.common import gpg
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import GpgKey, InstalledRPM, RPM

# (header, body) example packets from `sq packet dump` output
_SQ_V4_PUBKEY = (
    'Public-Key Packet, old CTB, 525 bytes',
    [
        '    Version: 4',
        '    Creation time: 2009-10-22 11:59:55 UTC',
        '    Pk algo: RSA',
        '    Pk size: 4096 bits',
        '    Fingerprint: 567E347AD0044ADE55BA8A5F199E2F91FD431D51',
        '    KeyID: 199E2F91FD431D51',
        '',
    ],
)
_SQ_V6_PUBKEY = (
    'Public-Key Packet, new CTB, 2659 bytes',
    [
        '    Version: 6',
        '    Creation time: 2025-10-08 17:40:03 UTC',
        '    Pk algo: ML-DSA-87+Ed448',
        '    Fingerprint: FCD355B305707A62DA143AB6E422397E50FE8467A2A95343D246D6276AFEDF8F',
        '    KeyID: FCD355B305707A62',
        '',
    ],
)
_SQ_USER_ID = (
    'User ID Packet, old CTB, 51 bytes',
    ['    Value: Red Hat, Inc. (release key 2) <security@redhat.com>', ''],
)
_SQ_SIGNATURE = (
    'Signature Packet, old CTB, 566 bytes',
    ['    Version: 4', '    Type: PositiveCertification', ''],
)


def _packets_to_dump(packets):
    """Flatten a list of (header, body) packets into `sq packet dump`-style lines."""
    lines = []
    for header, body in packets:
        lines.append(header)
        lines.extend(body)
    return lines


def _packet_body_without(body, field):
    """Drop the given field line (e.g. 'Version') from a packet body."""
    return [line for line in body if not line.strip().startswith(field + ':')]


def _packet_body_with_version(body, version):
    """Replace the Version line in a packet body with the given version."""
    new_body = []
    for line in body:
        if line.strip().startswith('Version:'):
            new_body.append('    Version: {}'.format(version))
        else:
            new_body.append(line)
    return new_body


def _touch(path):
    with open(path, 'w'):
        pass


def _make_pqc_subdir(root):
    pqc_dir = os.path.join(root, gpg.GPG_PQC_CERTS_SUBFOLDER)
    os.mkdir(pqc_dir)
    return pqc_dir


@pytest.mark.parametrize('target, product_type, distro, exp', [
    ('9.0', 'beta', 'rhel', '../../files/distro/rhel/rpm-gpg/9beta'),
    ('9.2', 'ga', 'rhel', '../../files/distro/rhel/rpm-gpg/9'),
    ('10.0', 'ga', 'rhel', '../../files/distro/rhel/rpm-gpg/10'),
    ('10', 'ga', 'centos', '../../files/distro/centos/rpm-gpg/10'),
    ('9.6', 'ga', 'almalinux', '../../files/distro/almalinux/rpm-gpg/9'),
    ('10.0', 'ga', 'almalinux', '../../files/distro/almalinux/rpm-gpg/10'),
])
def test_get_path_to_gpg_certs(monkeypatch, target, product_type, distro, exp):
    current_actor = CurrentActorMocked(dst_ver=target, dst_distro=distro,
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


def test_iter_gpg_keyfiles_excludes_pqc(leapp_tmpdir):
    _touch(os.path.join(leapp_tmpdir, 'key1'))
    _touch(os.path.join(leapp_tmpdir, 'key2'))
    _touch(os.path.join(_make_pqc_subdir(leapp_tmpdir), 'pqckey'))

    result = {os.path.basename(p) for p in gpg.iter_gpg_keyfiles(leapp_tmpdir, include_pqc=False)}
    # the 'pqc' subdirectory itself is not yielded (only files) and its content is excluded
    assert result == {'key1', 'key2'}


def test_iter_gpg_keyfiles_includes_pqc(leapp_tmpdir):
    _touch(os.path.join(leapp_tmpdir, 'key1'))
    _touch(os.path.join(_make_pqc_subdir(leapp_tmpdir), 'pqckey'))

    result = {os.path.basename(p) for p in gpg.iter_gpg_keyfiles(leapp_tmpdir, include_pqc=True)}
    assert result == {'key1', 'pqckey'}


def test_iter_gpg_keyfiles_missing_pqc_subdir(leapp_tmpdir):
    _touch(os.path.join(leapp_tmpdir, 'key1'))

    # no 'pqc' subdirectory present - yields only top-level files without an error
    result = {os.path.basename(p) for p in gpg.iter_gpg_keyfiles(leapp_tmpdir, include_pqc=True)}
    assert result == {'key1'}


@pytest.mark.parametrize('packets', [
    [],
    [_SQ_V4_PUBKEY],
    # multiple packets of mixed type, incl. blank separator lines in the bodies
    [_SQ_V4_PUBKEY, _SQ_USER_ID, _SQ_V6_PUBKEY],
])
def test_iter_sq_packets_round_trips(packets):
    # splitting is the inverse of concatenating header + body lines: whatever we
    # flatten in must come back out grouped exactly the same way
    assert list(gpg._iter_sq_packets(_packets_to_dump(packets))) == packets


def test_iter_sq_packets_drops_body_before_first_header():
    # indented lines with no preceding header are not attributed to any packet
    dump = ['    orphan body line'] + _packets_to_dump([_SQ_V4_PUBKEY])

    assert list(gpg._iter_sq_packets(dump)) == [_SQ_V4_PUBKEY]


@pytest.mark.parametrize('pubkey, expected_short_id', [
    (_SQ_V4_PUBKEY, 'fd431d51'),
    (_SQ_V6_PUBKEY, '05707a62'),
])
def test_parse_public_key_packet_sq_returns_short_key_id(pubkey, expected_short_id):
    _header, body = pubkey
    assert gpg._parse_public_key_packet_sq(body, '/some/key') == expected_short_id


@pytest.mark.parametrize('body', [
    _packet_body_without(_SQ_V4_PUBKEY[1], 'Version'),
    _packet_body_without(_SQ_V4_PUBKEY[1], 'Fingerprint'),
    [],
])
def test_parse_public_key_packet_sq_missing_field_raises(body):
    with pytest.raises(gpg.GpgParseError):
        gpg._parse_public_key_packet_sq(body, '/some/key')


def test_parse_public_key_packet_sq_unexpected_version_raises():
    # only v4 and v6 short-key-id slices are known; any other version is an error
    body = _packet_body_with_version(_SQ_V4_PUBKEY[1], '5')

    with pytest.raises(gpg.GpgParseError):
        gpg._parse_public_key_packet_sq(body, '/some/key')


def test_parse_gpg_key_sq_returns_pubkey_short_ids(monkeypatch):
    dump = _packets_to_dump([_SQ_V4_PUBKEY, _SQ_USER_ID, _SQ_SIGNATURE, _SQ_V6_PUBKEY])
    monkeypatch.setattr(gpg, 'run', lambda *args, **kwargs: {'stdout': dump})

    # only Public-Key Packets are collected; user id and signature packets - the
    # latter also carrying a Version line - are ignored
    assert gpg._parse_gpg_key_sq('/some/key') == ['fd431d51', '05707a62']


@pytest.mark.parametrize('error', [
    OSError('sq is not installed'),
    CalledProcessError('failed', ['sq'], {'stdout': '', 'stderr': 'boom', 'exit_code': 1}),
])
def test_parse_gpg_key_sq_run_error_returns_empty(monkeypatch, error):
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)

    def failing_run(*args, **kwargs):
        raise error

    monkeypatch.setattr(gpg, 'run', failing_run)

    # a failure to run sq is logged and yields no keys, same as the gpg2 path
    assert gpg._parse_gpg_key_sq('/some/key') == []
    assert logger.errmsg


def test_parse_gpg_key_sq_skips_unparseable_key(monkeypatch):
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)
    # the first key is missing its Fingerprint and cannot be parsed; the valid
    # second key must still be returned
    broken = (_SQ_V4_PUBKEY[0], _packet_body_without(_SQ_V4_PUBKEY[1], 'Fingerprint'))
    dump = _packets_to_dump([broken, _SQ_V6_PUBKEY])
    monkeypatch.setattr(gpg, 'run', lambda *args, **kwargs: {'stdout': dump})

    assert gpg._parse_gpg_key_sq('/some/key') == ['05707a62']
    assert logger.errmsg


@pytest.mark.parametrize('src_ver, uses_sq', [
    # sq is only available since 9.8, older sources keep using gpg2
    ('9.6', False),
    ('9.7', False),
    ('9.8', True),
    ('10.0', True),
])
def test_get_gpg_fp_from_file_dispatches_on_source_version(monkeypatch, src_ver, uses_sq):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver))

    def unexpected(*args, **kwargs):
        raise AssertionError('wrong parser used for source version {}'.format(src_ver))

    if uses_sq:
        monkeypatch.setattr(gpg, '_parse_gpg_key_sq', lambda key_path: ['5a6340b3'])
        monkeypatch.setattr(gpg, '_gpg_show_keys', unexpected)
    else:
        monkeypatch.setattr(gpg, '_gpg_show_keys', lambda key_path: {'stdout': [], 'stderr': ''})
        monkeypatch.setattr(gpg, '_parse_fp_from_gpg', lambda res: ['5a6340b3'])
        monkeypatch.setattr(gpg, '_parse_gpg_key_sq', unexpected)

    assert gpg.get_gpg_fp_from_file('/some/key') == ['5a6340b3']
