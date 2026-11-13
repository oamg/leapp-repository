import os

import pytest
import rpm

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import trustedgpgkeys
from leapp.libraries.common.gpg import GpgKeyInfo, GpgReadError
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import GpgKey, InstalledRPM, MisplacedTrustedGpgKeys, RPM, TrustedGpgKeys
from leapp.utils.deprecation import suppress_deprecation

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


def _mock_rpmdb(monkeypatch, keys, pqc_keys=None):
    """
    Mock the keys parsed out of the regular rpmdb and, optionally, out of the pqrpmdb

    Querying the pqrpmdb is an error unless `pqc_keys` is given.
    """
    def mocked_get_parsed_keys_from_rpmdb(db_path=None):
        if db_path is None:
            return list(keys)
        assert db_path == trustedgpgkeys._PQRPM_DB_PATH
        if pqc_keys is None:
            raise AssertionError('the pqrpmdb must not be queried')
        return list(pqc_keys)

    monkeypatch.setattr(trustedgpgkeys, '_get_parsed_keys_from_rpmdb', mocked_get_parsed_keys_from_rpmdb)


def _mock_rpmdb_ascii(monkeypatch, ascii_strs, parsed=None):
    """
    Mock the raw ascii armors read out of the rpmdb and the keys parsed from them

    `parsed` maps an ascii armor to the keys it holds; an armor missing from it
    is treated as unreadable by the underlying tool.
    """
    parsed = parsed or {}

    def mocked_parse_gpg_key_from_ascii(ascii_str):
        if ascii_str not in parsed:
            raise GpgReadError(f'cannot read {ascii_str}')
        return parsed[ascii_str]

    monkeypatch.setattr(trustedgpgkeys, 'get_gpg_ascii_from_rpmdb', lambda name, db_path: ascii_strs)
    monkeypatch.setattr(trustedgpgkeys, 'parse_gpg_key_from_ascii', mocked_parse_gpg_key_from_ascii)


def test_get_parsed_keys_from_rpmdb_flattens_armors(monkeypatch):
    """
    Every gpg-pubkey holds one armor; the keys parsed out of them are returned as one list.
    """
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    _mock_rpmdb_ascii(
        monkeypatch,
        ['armor-1', 'armor-2'],
        {'armor-1': [_v4('fd431d51')], 'armor-2': [_v6('05707a62')]},
    )

    assert trustedgpgkeys._get_parsed_keys_from_rpmdb() == [_v4('fd431d51'), _v6('05707a62')]


def test_get_parsed_keys_from_rpmdb_skips_and_logs_unreadable_armor(monkeypatch):
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)
    # the unreadable armor is dropped while the valid one is still collected
    _mock_rpmdb_ascii(monkeypatch, ['broken', 'armor-1'], {'armor-1': [_v4('fd431d51')]})

    assert trustedgpgkeys._get_parsed_keys_from_rpmdb() == [_v4('fd431d51')]
    assert len(logger.errmsg) == 1


def test_get_parsed_keys_from_rpmdb_no_keys(monkeypatch):
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)
    _mock_rpmdb_ascii(monkeypatch, [])

    assert trustedgpgkeys._get_parsed_keys_from_rpmdb() == []
    assert logger.dbgmsg


def test_get_parsed_keys_from_rpmdb_query_error_raises(monkeypatch):
    def failing_query(*args, **kwargs):
        raise rpm.error('no such dbpath')

    monkeypatch.setattr(trustedgpgkeys, 'get_gpg_ascii_from_rpmdb', failing_query)

    # without the keys imported in the rpmdb there is no way to continue
    with pytest.raises(StopActorExecutionError):
        trustedgpgkeys._get_parsed_keys_from_rpmdb()


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


def test_parse_trusted_keyfiles_skips_and_logs_unreadable_keyfile(monkeypatch):
    """
    One unreadable keyfile does not stop the scan of the rest of the directory.
    """
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)
    good = os.path.join(_TRUSTED_DIR, 'v4key')
    broken = os.path.join(_TRUSTED_DIR, 'not-a-key')
    _mock_trusted_dir(monkeypatch, {good: [_v4('fd431d51')], broken: None})

    def mocked_parse_gpg_key_from_file(keyfile):
        if keyfile == broken:
            raise GpgReadError('no valid OpenPGP data found')
        return [_v4('fd431d51')]

    monkeypatch.setattr(trustedgpgkeys, 'parse_gpg_key_from_file', mocked_parse_gpg_key_from_file)

    assert trustedgpgkeys._parse_trusted_keyfiles(include_pqc=False) == {good: [_v4('fd431d51')]}
    assert len(logger.errmsg) == 1


def _as_tuple_set(pubkeys):
    """
    Reduce the (GpgKeyInfo, rpmdb, path) triples of _get_pubkeys to a comparable set.
    """
    return {(info.short_keyid, rpmdb, path) for info, rpmdb, path in pubkeys}


def test_get_pubkeys(monkeypatch):
    """
    Very basic test of _get_pubkeys function
    """
    rpm_fps = ['9570ff31', '99900000']
    file_fps = ['0000ff31', '0000ff32']

    # no pqrpm installed, so the pqrpmdb is not queried
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[_get_test_installed_rmps([])]))
    _mock_rpmdb(monkeypatch, [_v4(fp) for fp in rpm_fps])

    pubkeys = trustedgpgkeys._get_pubkeys({'/mydir/myfile': [_v4(fp) for fp in file_fps]})

    assert len(pubkeys) == len(rpm_fps + file_fps)
    assert _as_tuple_set(pubkeys) == (
        {(fp, True, None) for fp in rpm_fps} | {(fp, False, '/mydir/myfile') for fp in file_fps}
    )


def test_get_pubkeys_skips_keyfile_keys_already_in_rpmdb(monkeypatch):
    """
    A key present both in the rpmdb and in a keyfile is reported once, as an imported key.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[_get_test_installed_rmps([])]))
    _mock_rpmdb(monkeypatch, [_v4('9570ff31')])

    keyfiles_to_infos = {
        '/certs/imported': [_v4('9570ff31')],
        # the same key in two keyfiles is reported once too
        '/certs/custom': [_v4('0000ff31')],
        '/certs/custom-copy': [_v4('0000ff31')],
    }

    pubkeys = trustedgpgkeys._get_pubkeys(keyfiles_to_infos)

    assert len(pubkeys) == 2
    assert _as_tuple_set(pubkeys) == {
        ('9570ff31', True, None),
        ('0000ff31', False, '/certs/custom'),
    }


def test_get_pubkeys_skips_keyfile_key_already_in_pqrpmdb(monkeypatch):
    """
    A key present both in the pqrpmdb and in a keyfile is reported once.
    """
    installed_rpms = _get_test_installed_rmps([])
    installed_rpms.items.append(_make_rpm('pqrpm'))
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.9', msgs=[installed_rpms]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    # the key is only in the pqrpmdb, not in the regular rpmdb
    _mock_rpmdb(monkeypatch, [], pqc_keys=[_v6('05707a62')])

    pubkeys = trustedgpgkeys._get_pubkeys({os.path.join(_PQC_DIR, 'v6key'): [_v6('05707a62')]})

    # reported once, as an imported key rather than a keyfile one
    assert _as_tuple_set(pubkeys) == {('05707a62', True, None)}


def test_get_pubkeys_does_not_collapse_short_keyid_collisions(monkeypatch):
    """
    Two different keys sharing a short key id are both kept.

    Deduplication has to be done on the full fingerprint; the short key id is
    8 characters and is not collision resistant, which is the whole reason the
    full fingerprint is reported at all.
    """
    rpmdb_key = _v4('fd431d51')
    # same short key id, different full fingerprint
    keyfile_key = GpgKeyInfo(fingerprint='f' * 32 + 'fd431d51', short_keyid='fd431d51', is_pqc=False)
    assert rpmdb_key.fingerprint != keyfile_key.fingerprint

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[_get_test_installed_rmps([])]))
    _mock_rpmdb(monkeypatch, [rpmdb_key])

    pubkeys = trustedgpgkeys._get_pubkeys({'/certs/custom': [keyfile_key]})

    assert len(pubkeys) == 2
    assert {info.fingerprint for info, _rpmdb, _path in pubkeys} == {
        rpmdb_key.fingerprint,
        keyfile_key.fingerprint,
    }


@pytest.mark.parametrize('source_version, has_pqrpm, should_include_pqc', [
    ('9.6', False, False),
    ('9.8', False, False),
    ('9.8', True, False),
    ('9.9', False, False),
    ('9.9', True, True),
    ('9.10', True, True),
    ('10.1', False, False),
    ('10.4', False, False),
])
def test_get_pubkeys_merges_pqrpmdb_keys_without_duplicates(
    monkeypatch, has_pqrpm, source_version, should_include_pqc
):
    installed_rpms = _get_test_installed_rmps([])
    if has_pqrpm:
        installed_rpms.items.append(_make_rpm('pqrpm'))
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=source_version, msgs=[installed_rpms]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    # 05707a62 is in both the regular rpmdb and the pqrpmdb; b2973cf6 is pqrpmdb-only
    _mock_rpmdb(
        monkeypatch,
        [_v4('9570ff31'), _v6('05707a62')],
        pqc_keys=[_v6('b2973cf6'), _v6('05707a62')] if should_include_pqc else None,
    )

    pubkeys = trustedgpgkeys._get_pubkeys({})

    # the pqrpmdb-only key is added, the overlapping one is not duplicated
    if should_include_pqc:
        assert len(pubkeys) == 3
        assert {info.short_keyid for info, _rpmdb, _path in pubkeys} == {'9570ff31', '05707a62', 'b2973cf6'}
    else:
        assert len(pubkeys) == 2
        assert {info.short_keyid for info, _rpmdb, _path in pubkeys} == {'9570ff31', '05707a62'}
    assert all(rpmdb for _info, rpmdb, _path in pubkeys)


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
        # the expected values below are short key ids; GpgPubKey.fingerprint is
        # the full fingerprint, so the two must not be confused here
        assert all(key.fingerprint != key.short_keyid for key in keys)
        return [(key.path, key.short_keyid) for key in keys]

    assert as_tuples(misplaced_pqc) == expected_pqc
    assert as_tuples(misplaced_classic) == expected_classic


@suppress_deprecation(GpgKey)
def test_process(monkeypatch):
    """
    Executes the "main" function
    """
    installed_rpms = _get_test_installed_rmps([])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms], src_ver='9.9'))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    _mock_rpmdb(monkeypatch, [_v4('9570ff31')])
    _mock_trusted_dir(monkeypatch, {
        os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')],
        os.path.join(_PQC_DIR, 'v6key'): [_v6('05707a62')],
    })

    trustedgpgkeys.process()

    # the layout of the trusted directory is correct, only the trusted keys are produced
    assert api.produce.called == 1
    produced = api.produce.model_instances[0]
    assert isinstance(produced, TrustedGpgKeys)
    assert {key.short_keyid for key in produced.keys} == {'9570ff31', 'fd431d51', '05707a62'}
    # the deprecated 'items' holds the short key id in its 'fingerprint' field
    assert {key.fingerprint for key in produced.items} == {'9570ff31', 'fd431d51', '05707a62'}


@suppress_deprecation(GpgKey)
def test_process_keys_and_items_describe_the_same_keys(monkeypatch):
    """
    The deprecated 'items' list cannot silently drift from the new 'keys' list.

    GpgKey.fingerprint holds the short key id while GpgPubKey.fingerprint holds
    the full one, so the two lists are only comparable field by field.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[_get_test_installed_rmps([])], src_ver='9.9'))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    _mock_rpmdb(monkeypatch, [_v4('9570ff31'), _v6('05707a62')])
    _mock_trusted_dir(monkeypatch, {os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')]})

    trustedgpgkeys.process()

    produced = api.produce.model_instances[0]
    assert len(produced.keys) == len(produced.items) == 3
    assert (
        [(k.short_keyid, k.rpmdb, k.path) for k in produced.keys]
        == [(i.fingerprint, i.rpmdb, i.filename) for i in produced.items]
    )


@suppress_deprecation(GpgKey)
def test_process_reports_both_fingerprint_forms(monkeypatch):
    """
    Only the new model can report the full fingerprint of a key.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[_get_test_installed_rmps([])], src_ver='9.9'))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    _mock_rpmdb(monkeypatch, [_v6('05707a62')])
    _mock_trusted_dir(monkeypatch, {})

    trustedgpgkeys.process()

    produced = api.produce.model_instances[0]
    assert produced.keys[0].fingerprint == _v6('05707a62').fingerprint
    assert produced.keys[0].short_keyid == '05707a62'
    assert produced.keys[0].rpmdb is True
    assert produced.keys[0].path is None
    # the deprecated model has no field able to carry the full fingerprint
    assert produced.items[0].fingerprint == '05707a62'
    assert not hasattr(produced.items[0], 'full_fingerprint')


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
    _mock_rpmdb(monkeypatch, [])
    _mock_trusted_dir(monkeypatch, {
        os.path.join(_TRUSTED_DIR, 'v4key'): [_v4('fd431d51')],
        os.path.join(_PQC_DIR, 'v6key'): [_v6('05707a62')],
    })

    trustedgpgkeys.process()

    trusted_keys = api.produce.model_instances[0]
    expected = {'fd431d51', '05707a62'} if has_sq else {'fd431d51'}
    assert {key.short_keyid for key in trusted_keys.keys} == expected


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
    _mock_rpmdb(monkeypatch, [])
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
    assert [(key.path, key.short_keyid) for key in misplaced[0].pqc_keys] == [
        (os.path.join(_TRUSTED_DIR, 'misplaced-pqc'), '05707a62')
    ]
    assert [(key.path, key.short_keyid) for key in misplaced[0].classic_keys] == [
        (os.path.join(_PQC_DIR, 'misplaced-classic'), '199e2f91')
    ]
