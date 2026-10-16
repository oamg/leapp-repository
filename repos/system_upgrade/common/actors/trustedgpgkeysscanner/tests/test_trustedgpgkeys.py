import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import trustedgpgkeys
from leapp.libraries.common.gpg import get_pubkeys_from_rpms
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import GpgKey, InstalledRPM, RPM, TrustedGpgKeys


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


# stdout of 'rpm -qa --dbpath <pqrpmdb>'; warnings about v6 keys go to stderr
_PQRPMDB_STDOUT = [
    'gpg-pubkey-b2973cf6-5dfd1395',
    'gpg-pubkey-05707a62-68e6a1f3',
]


class MockedGetGpgFromFile:
    def __init__(self, file_fps_tuples):
        # e.g. file_fps_tuple = [('/mydir/myfile', ['0000ff31', '0000ff32'])]
        self._data = {}
        for fname, fps in file_fps_tuples:
            self._data[fname] = fps

    def get_files(self):
        return self._data.keys()

    def __call__(self, fname):
        return self._data.get(fname, [])


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


def test_get_pubkeys(monkeypatch):
    """
    Very basic test of _get_pubkeys function
    """
    rpm_fps = ['9570ff31', '99900000']
    file_fps = ['0000ff31', '0000ff32']
    installed_rpms = _get_test_installed_rmps(rpm_fps)
    mocked_gpg_files = MockedGetGpgFromFile([('/mydir/myfile', ['0000ff31', '0000ff32'])])

    def unexpected(*args, **kwargs):
        raise AssertionError('the pqrpmdb must not be queried without pqrpm installed')

    # no pqrpm installed, so the pqrpmdb is not queried
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms]))
    monkeypatch.setattr(trustedgpgkeys, 'run', unexpected)
    monkeypatch.setattr(
        trustedgpgkeys, 'iter_gpg_keyfiles',
        lambda include_pqc: iter(mocked_gpg_files.get_files())
    )
    monkeypatch.setattr(trustedgpgkeys, 'get_gpg_fp_from_file', mocked_gpg_files)

    pubkeys = trustedgpgkeys._get_pubkeys(installed_rpms)
    assert len(pubkeys) == len(rpm_fps + file_fps)
    assert set(rpm_fps) == {pkey.fingerprint for pkey in pubkeys if pkey.rpmdb}
    assert set(file_fps) == {pkey.fingerprint for pkey in pubkeys if not pkey.rpmdb}
    assert list({pkey.filename for pkey in pubkeys if not pkey.rpmdb})[0] == '/mydir/myfile'


def test_get_pubkeys_includes_pqc_keyfiles(monkeypatch):
    """
    Keys from the 'pqc' subdirectory are scanned and become trusted keys.
    """
    installed_rpms = _get_test_installed_rmps([])
    mocked_gpg_files = MockedGetGpgFromFile([
        ('/certs/v4key', ['fd431d51']),
        ('/certs/pqc/v6key', ['05707a62']),
    ])

    # the pqc keyfile is only discovered when PQC keys are requested
    def mocked_iter_gpg_keyfiles(include_pqc):
        files = ['/certs/v4key']
        if include_pqc:
            files.append('/certs/pqc/v6key')
        return iter(files)

    # no pqrpm installed, so the pqrpmdb is not queried
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms]))
    monkeypatch.setattr(trustedgpgkeys, 'iter_gpg_keyfiles', mocked_iter_gpg_keyfiles)
    monkeypatch.setattr(trustedgpgkeys, 'get_gpg_fp_from_file', mocked_gpg_files)

    pubkeys = trustedgpgkeys._get_pubkeys(installed_rpms)

    file_fps = {pkey.fingerprint for pkey in pubkeys if not pkey.rpmdb}
    # both the top-level v4 key and the pqc-subdir v6 key are trusted
    assert file_fps == {'fd431d51', '05707a62'}


def test_get_pubkeys_merges_pqrpmdb_keys_without_duplicates(monkeypatch):
    # 05707a62 is in both the regular rpmdb and the pqrpmdb; b2973cf6 is pqrpmdb-only
    installed_rpms = _get_test_installed_rmps(['9570ff31', '05707a62'])
    installed_rpms.items.append(_make_rpm('pqrpm'))
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[installed_rpms]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(trustedgpgkeys, 'iter_gpg_keyfiles', lambda include_pqc: iter([]))
    monkeypatch.setattr(trustedgpgkeys, 'run', lambda *args, **kwargs: {'stdout': _PQRPMDB_STDOUT})

    pubkeys = trustedgpgkeys._get_pubkeys(installed_rpms)

    # the pqrpmdb-only key is added, the overlapping one is not duplicated
    assert len(pubkeys) == 3
    assert {k.fingerprint for k in pubkeys} == {'9570ff31', '05707a62', 'b2973cf6'}
    assert all(k.rpmdb for k in pubkeys)


def test_process(monkeypatch):
    """
    Executes the "main" function
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[_get_test_installed_rmps(['9570ff31'])])
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(trustedgpgkeys, '_get_pubkeys', get_pubkeys_from_rpms)

    trustedgpgkeys.process()
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], TrustedGpgKeys)
    assert reporting.create_report.called == 0
