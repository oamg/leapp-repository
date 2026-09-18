import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import trustedgpgkeys
from leapp.libraries.common.gpg import GpgKeyInfo
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import GpgKey, InstalledRPM, MisplacedTrustedGpgKeys, RPM, TrustedGpgKeys

_TRUSTED_DIR = '/certs'
_PQC_DIR = os.path.join(_TRUSTED_DIR, 'pqc')


def _get_test_installed_rmps(fps):
    # adding at least one rpm that is not gpg-pubkey
    rpms = [RPM(
        name='rpm',
        version='4.17.1',
        release='3.fc35',
        epoch='0',
        packager='Fedora Project',
        arch='x86_64',
        pgpsig='RSA/SHA256, Tue 02 Aug 2022 03:12:43 PM CEST, Key ID db4639719867c58f'
    )]
    for fp in fps:
        rpms.append(RPM(
            name='gpg-pubkey',
            version=fp,
            release='5e3006fb',
            epoch='0',
            packager='Fedora (33) <fedora-33-primary@fedoraproject.org>',
            arch='noarch',
            pgpsig=''
        ))
    return InstalledRPM(items=rpms)


def _make_rpm(name, version='1.0'):
    return RPM(name=name, version=version, release='1', epoch='0', packager='', arch='x86_64', pgpsig='')


def _v4(short_keyid):
    # the short key id of a v4 key is the last 8 characters of its fingerprint
    return GpgKeyInfo(fingerprint='0' * 32 + short_keyid, short_keyid=short_keyid, is_pqc=False)


def _v6(short_keyid):
    # the short key id of a v6 key is the 9th-16th character of its fingerprint
    return GpgKeyInfo(fingerprint='0' * 8 + short_keyid + '0' * 48, short_keyid=short_keyid, is_pqc=True)


def _mock_trusted_dir(monkeypatch, keyfiles):
    """
    Mock the trusted keys directory with the given {keyfile: [GpgKeyInfo, ...]} content
    """
    def mocked_iter_gpg_keyfiles(include_pqc):
        # mirror the real iter_gpg_keyfiles: skip the 'pqc' subdirectory unless include_pqc
        for keyfile in keyfiles:
            if not include_pqc and os.path.dirname(keyfile) == _PQC_DIR:
                continue
            yield keyfile

    monkeypatch.setattr(trustedgpgkeys, 'get_path_to_gpg_certs', lambda: _TRUSTED_DIR)
    monkeypatch.setattr(trustedgpgkeys, 'iter_gpg_keyfiles', mocked_iter_gpg_keyfiles)
    monkeypatch.setattr(trustedgpgkeys, 'parse_gpg_key_from_file', lambda keyfile: keyfiles[keyfile])


# stdout of 'rpm -qa --dbpath <pqrpmdb>'; warnings about v6 keys go to stderr
_PQRPMDB_STDOUT = [
    'gpg-pubkey-b2973cf6-5dfd1395',
    'gpg-pubkey-05707a62-68e6a1f3',
]


def test_get_pubkeys_from_pqrmdb_parses_short_key_ids(monkeypatch):
    """
    The version (short key id) of every gpg-pubkey package in the pqrpmdb is collected.
    """
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(trustedgpgkeys, 'run', lambda *args, **kwargs: {'stdout': _PQRPMDB_STDOUT})

    keys = trustedgpgkeys._get_pubkeys_from_pqrmdb()

    # incl. the v6 (pqc) key 05707a62; all are marked as imported (rpmdb=True)
    assert keys == [
        GpgKey(fingerprint='b2973cf6', rpmdb=True),
        GpgKey(fingerprint='05707a62', rpmdb=True),
    ]


@pytest.mark.parametrize('bad_line', [
    'gpg-pubkey-05707a62',               # too few fields
    'gpg-notpubkey-05707a62-68e6a1f3',   # not a gpg-pubkey package
    'gpg-pubkey-abc-68e6a1f3',           # key id is not 8 characters
    '',                                  # empty line
])
def test_get_pubkeys_from_pqrmdb_skips_and_logs_malformed(monkeypatch, bad_line):
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)
    # the bad line is dropped while the surrounding valid line is still collected
    stdout = ['gpg-pubkey-05707a62-68e6a1f3', bad_line]
    monkeypatch.setattr(trustedgpgkeys, 'run', lambda *args, **kwargs: {'stdout': stdout})

    keys = trustedgpgkeys._get_pubkeys_from_pqrmdb()

    assert keys == [GpgKey(fingerprint='05707a62', rpmdb=True)]
    assert len(logger.errmsg) == 1


def test_get_pubkeys_from_pqrmdb_run_error_raises(monkeypatch):
    def failing_run(*args, **kwargs):
        raise CalledProcessError('failed', ['rpm'], {'stdout': '', 'stderr': 'boom', 'exit_code': 1})

    monkeypatch.setattr(trustedgpgkeys, 'run', failing_run)

    with pytest.raises(StopActorExecutionError):
        trustedgpgkeys._get_pubkeys_from_pqrmdb()


@pytest.mark.parametrize('include_pqc', [True, False])
def test_parse_trusted_keyfiles(monkeypatch, include_pqc):
    """
    Every keyfile in the trusted directory is mapped to the keys it contains.

    The keyfiles in the 'pqc' subdirectory are only read when the PQC keys are requested.
    """
    keyfiles = {
        os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')],
        os.path.join(_PQC_DIR, 'v6key'): [_v6('05707a62')],
    }
    _mock_trusted_dir(monkeypatch, keyfiles)

    keyfiles_to_infos = trustedgpgkeys._parse_trusted_keyfiles(include_pqc=include_pqc)

    expected = dict(keyfiles) if include_pqc else {os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')]}
    assert keyfiles_to_infos == expected


def test_get_pubkeys(monkeypatch):
    """
    Very basic test of _get_pubkeys function
    """
    rpm_fps = ['9570ff31', '99900000']
    file_fps = ['0000ff31', '0000ff32']
    installed_rpms = _get_test_installed_rmps(rpm_fps)

    def unexpected(*args, **kwargs):
        raise AssertionError('the pqrpmdb must not be queried without pqrpm installed')

    # no pqrpm installed, so the pqrpmdb is not queried
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms]))
    monkeypatch.setattr(trustedgpgkeys, 'run', unexpected)

    pubkeys = trustedgpgkeys._get_pubkeys(installed_rpms, {'/mydir/myfile': file_fps})

    assert len(pubkeys) == len(rpm_fps + file_fps)
    assert set(rpm_fps) == {pkey.fingerprint for pkey in pubkeys if pkey.rpmdb}
    assert set(file_fps) == {pkey.fingerprint for pkey in pubkeys if not pkey.rpmdb}
    assert list({pkey.filename for pkey in pubkeys if not pkey.rpmdb})[0] == '/mydir/myfile'


def test_get_pubkeys_skips_keyfile_keys_already_in_rpmdb(monkeypatch):
    """
    A key present both in the rpmdb and in a keyfile is reported once, as an imported key.
    """
    installed_rpms = _get_test_installed_rmps(['9570ff31'])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms]))

    keyfiles_to_fps = {
        '/certs/imported': ['9570ff31'],
        # the same key in two keyfiles is reported once too
        '/certs/custom': ['0000ff31'],
        '/certs/custom-copy': ['0000ff31'],
    }

    pubkeys = trustedgpgkeys._get_pubkeys(installed_rpms, keyfiles_to_fps)

    assert len(pubkeys) == 2
    assert {(k.fingerprint, k.rpmdb, k.filename) for k in pubkeys} == {
        ('9570ff31', True, None),
        ('0000ff31', False, '/certs/custom'),
    }


def test_get_pubkeys_merges_pqrpmdb_keys_without_duplicates(monkeypatch):
    # 05707a62 is in both the regular rpmdb and the pqrpmdb; b2973cf6 is pqrpmdb-only
    installed_rpms = _get_test_installed_rmps(['9570ff31', '05707a62'])
    installed_rpms.items.append(_make_rpm('pqrpm'))
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(trustedgpgkeys, 'run', lambda *args, **kwargs: {'stdout': _PQRPMDB_STDOUT})

    pubkeys = trustedgpgkeys._get_pubkeys(installed_rpms, {})

    # the pqrpmdb-only key is added, the overlapping one is not duplicated
    assert len(pubkeys) == 3
    assert {k.fingerprint for k in pubkeys} == {'9570ff31', '05707a62', 'b2973cf6'}
    assert all(k.rpmdb for k in pubkeys)


@pytest.mark.parametrize('keyfiles, expected_pqc, expected_classic', [
    # the correct layout: v4 keys at the top-level, v6 keys in the 'pqc' subdirectory
    (
        {
            os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')],
            os.path.join(_PQC_DIR, 'v6key'): [_v6('05707a62')],
        },
        [],
        [],
    ),
    # a v6 key at the top-level belongs to the 'pqc' subdirectory
    (
        {
            os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')],
            os.path.join(_TRUSTED_DIR, 'misplaced'): [_v6('05707a62')],
        },
        [(os.path.join(_TRUSTED_DIR, 'misplaced'), '05707a62')],
        [],
    ),
    # a v4 key in the 'pqc' subdirectory belongs to the top-level
    (
        {
            os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')],
            os.path.join(_PQC_DIR, 'misplaced'): [_v4('199e2f91')],
        },
        [],
        [(os.path.join(_PQC_DIR, 'misplaced'), '199e2f91')],
    ),
    # only the v6 key of a mixed keyfile at the top-level is misplaced
    (
        {os.path.join(_TRUSTED_DIR, 'mixed'): [_v4('fd431d51'), _v6('05707a62')]},
        [(os.path.join(_TRUSTED_DIR, 'mixed'), '05707a62')],
        [],
    ),
    # only the v4 key of a mixed keyfile in the 'pqc' subdirectory is misplaced
    (
        {os.path.join(_PQC_DIR, 'mixed'): [_v4('fd431d51'), _v6('05707a62')]},
        [],
        [(os.path.join(_PQC_DIR, 'mixed'), 'fd431d51')],
    ),
    # both kinds of misplaced keys are detected at once
    (
        {
            os.path.join(_TRUSTED_DIR, 'misplaced'): [_v6('05707a62')],
            os.path.join(_PQC_DIR, 'misplaced'): [_v4('199e2f91')],
        },
        [(os.path.join(_TRUSTED_DIR, 'misplaced'), '05707a62')],
        [(os.path.join(_PQC_DIR, 'misplaced'), '199e2f91')],
    ),
])
def test_get_misplaced_keyfiles(monkeypatch, keyfiles, expected_pqc, expected_classic):
    _mock_trusted_dir(monkeypatch, keyfiles)

    misplaced_pqc, misplaced_classic = trustedgpgkeys._get_misplaced_keyfiles(keyfiles)

    def as_tuples(keys):
        # the misplaced keys always come from a keyfile, never from the rpmdb
        assert all(not key.rpmdb for key in keys)
        return [(key.filename, key.fingerprint) for key in keys]

    assert as_tuples(misplaced_pqc) == expected_pqc
    assert as_tuples(misplaced_classic) == expected_classic


def test_process_no_installed_rpms_raises(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    with pytest.raises(StopActorExecutionError):
        trustedgpgkeys.process()

    assert api.produce.called == 0


def test_process(monkeypatch):
    """
    Executes the "main" function
    """
    installed_rpms = _get_test_installed_rmps(['9570ff31'])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms], src_ver='9.9'))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    _mock_trusted_dir(monkeypatch, {
        os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')],
        os.path.join(_PQC_DIR, 'v6key'): [_v6('05707a62')],
    })

    trustedgpgkeys.process()

    # the layout of the trusted directory is correct, only the trusted keys are produced
    assert api.produce.called == 1
    produced = api.produce.model_instances[0]
    assert isinstance(produced, TrustedGpgKeys)
    assert {key.fingerprint for key in produced.items} == {'9570ff31', 'fd431d51', '05707a62'}


@pytest.mark.parametrize('src_ver, has_sq', [
    ('8.10', False),
    ('9.7', False),
    ('9.8', False),
    ('9.9', True),
    ('9.10', True),
])
def test_process_scans_pqc_keyfiles_with_sq_only(monkeypatch, src_ver, has_sq):
    """
    The keys from the 'pqc' subdirectory are trusted on source systems with 'sq' only.

    Without 'sq' the v6 keys cannot be parsed at all, so the subdirectory is not scanned.
    """
    installed_rpms = _get_test_installed_rmps([])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms], src_ver=src_ver))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    _mock_trusted_dir(monkeypatch, {
        os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')],
        os.path.join(_PQC_DIR, 'v6key'): [_v6('05707a62')],
    })

    trustedgpgkeys.process()

    trusted_keys = api.produce.model_instances[0]
    expected = {'fd431d51', '05707a62'} if has_sq else {'fd431d51'}
    assert {key.fingerprint for key in trusted_keys.items} == expected


@pytest.mark.parametrize('src_ver, produces_misplaced', [
    # without 'sq' the misplaced v6 keys cannot be detected, so nothing is produced
    ('8.10', False),
    ('9.8', False),
    ('9.9', True),
    ('9.10', True),
])
def test_process_produces_misplaced_keys(monkeypatch, src_ver, produces_misplaced):
    """
    The misplaced keys are reported in a separate message on source systems with 'sq'.
    """
    installed_rpms = _get_test_installed_rmps([])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms], src_ver=src_ver))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    _mock_trusted_dir(monkeypatch, {
        # a v6 key at the top-level and a v4 key in the 'pqc' subdirectory
        os.path.join(_TRUSTED_DIR, 'misplaced-pqc'): [_v6('05707a62')],
        os.path.join(_PQC_DIR, 'misplaced-classic'): [_v4('199e2f91')],
    })

    trustedgpgkeys.process()

    misplaced = [msg for msg in api.produce.model_instances if isinstance(msg, MisplacedTrustedGpgKeys)]
    if not produces_misplaced:
        assert not misplaced
        return

    assert len(misplaced) == 1
    assert [(key.filename, key.fingerprint) for key in misplaced[0].pqc_keys] == [
        (os.path.join(_TRUSTED_DIR, 'misplaced-pqc'), '05707a62')
    ]
    assert [(key.filename, key.fingerprint) for key in misplaced[0].classic_keys] == [
        (os.path.join(_PQC_DIR, 'misplaced-classic'), '199e2f91')
    ]
