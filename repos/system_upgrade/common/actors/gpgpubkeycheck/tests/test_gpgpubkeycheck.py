import pytest
import rpm

from leapp import reporting
from leapp.libraries.actor import gpgpubkeycheck
from leapp.libraries.common.gpg import GpgKeyInfo, GpgReadError
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import GpgPubKey, TrustedGpgKeys

# full fingerprints: the two keys of the RHEL release keyfile and a v6 key that is not trusted
_RH_FP = '567e347ad0044ade55ba8a5f199e2f91fd431d51'
_AUX_FP = '7e4624258c406535d56d6f135054e4a45a6340b3'
_UNTRUSTED_FP = 'fcd355b305707a62da143ab6e422397e50fe8467a2a95343d246d6276afedf8f'

_RH_PACKAGER = 'Red Hat, Inc. (release key 2) <security@redhat.com>'
_UNTRUSTED_PACKAGER = 'Somebody Else <nobody@example.com>'

# the ascii armors are opaque to the actor; parse_gpg_key_from_ascii is always mocked
_RH_ARMOR = 'armor-of-the-release-key'
_AUX_ARMOR = 'armor-of-the-auxiliary-key'
_UNTRUSTED_ARMOR = 'armor-of-an-unexpected-key'
_BROKEN_ARMOR = 'armor-that-cannot-be-read'
_TWO_KEYS_ARMOR = 'armor-holding-two-primary-keys'

_ARMOR_TO_KEYS = {
    _RH_ARMOR: [GpgKeyInfo(fingerprint=_RH_FP, short_keyid='fd431d51', is_pqc=False)],
    _AUX_ARMOR: [GpgKeyInfo(fingerprint=_AUX_FP, short_keyid='5a6340b3', is_pqc=False)],
    _UNTRUSTED_ARMOR: [GpgKeyInfo(fingerprint=_UNTRUSTED_FP, short_keyid='05707a62', is_pqc=True)],
    # neither of these can produce a usable (fingerprint, packager) tuple
    _BROKEN_ARMOR: GpgReadError('no valid OpenPGP data found'),
    _TWO_KEYS_ARMOR: [
        GpgKeyInfo(fingerprint=_RH_FP, short_keyid='fd431d51', is_pqc=False),
        GpgKeyInfo(fingerprint=_AUX_FP, short_keyid='5a6340b3', is_pqc=False),
    ],
}

_TITLE_CANNOT_CHECK = 'Cannot perform the check of installed GPG keys after the upgrade.'
_TITLE_UNEXPECTED = 'Detected unexpected GPG keys after the upgrade.'


def _header(armor, name='gpg-pubkey-fd431d51-4ae0493b', packager=_RH_PACKAGER):
    """
    Minimal stand-in for an rpm header - the actor only ever reads these three tags.
    """
    return {
        rpm.RPMTAG_DESCRIPTION: armor,
        rpm.RPMTAG_NAME: name,
        rpm.RPMTAG_PACKAGER: packager,
    }


class _FakeTransactionSet:
    def __init__(self, headers, error=None):
        self._headers = headers
        self._error = error

    def dbMatch(self, tag, value):  # noqa: N802; mirrors the name of the rpm binding's method
        assert (tag, value) == ('name', 'gpg-pubkey')
        if self._error is not None:
            raise self._error
        return self._headers


def _setup(monkeypatch, headers=(), trusted=None, rpm_error=None, nogpgcheck=False):
    """
    :param headers: the gpg-pubkey headers the rpmdb query yields
    :param trusted: full fingerprints to put in TrustedGpgKeys; None produces no message at all
    :param rpm_error: an rpm.error to raise from the rpmdb query instead of yielding headers
    :param nogpgcheck: run with LEAPP_NOGPGCHECK=1
    """
    msgs = []
    if trusted is not None:
        # short_keyid is irrelevant here, the actor matches on the full fingerprint only
        msgs.append(TrustedGpgKeys(
            keys=[GpgPubKey(fingerprint=fp, short_keyid=fp[-8:], rpmdb=True) for fp in trusted]
        ))

    envars = {'LEAPP_NOGPGCHECK': '1'} if nogpgcheck else None
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars=envars, msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(
        gpgpubkeycheck.rpm, 'TransactionSet', lambda: _FakeTransactionSet(list(headers), rpm_error)
    )

    def mocked_parse_gpg_key_from_ascii(ascii_armor):
        result = _ARMOR_TO_KEYS[ascii_armor]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(gpgpubkeycheck, 'parse_gpg_key_from_ascii', mocked_parse_gpg_key_from_ascii)


def _assert_cannot_check_report(cause):
    """
    Assert the last report is the 'cannot check' one and names the given cause.
    """
    assert reporting.create_report.called == 1
    report = reporting.create_report.report_fields
    assert report['title'] == _TITLE_CANNOT_CHECK
    assert report['severity'] == reporting.Severity.HIGH
    assert reporting.Groups.SECURITY in report['groups']
    # the check is informative only, it must never block the finished upgrade
    assert reporting.Groups.INHIBITOR not in report['groups']
    assert cause in report['summary']


def test_nogpgcheck_skips_check(monkeypatch):
    """
    With --nogpgcheck nothing is reported even though an unexpected key is installed.
    """
    _setup(monkeypatch, headers=[_header(_UNTRUSTED_ARMOR)], trusted=[], nogpgcheck=True)

    gpgpubkeycheck.process()

    assert reporting.create_report.called == 0
    assert any('--nogpgcheck option is used' in msg for msg in api.current_logger.warnmsg)


@pytest.mark.parametrize('headers, trusted', [
    # every installed key is trusted
    ([_header(_RH_ARMOR), _header(_AUX_ARMOR)], [_RH_FP, _AUX_FP]),
    # more keys are trusted than are installed - not every trusted key has to be imported
    ([_header(_RH_ARMOR)], [_RH_FP, _AUX_FP]),
    # no gpg-pubkey is imported at all
    ([], [_RH_FP]),
])
def test_no_unexpected_keys_no_report(monkeypatch, headers, trusted):
    _setup(monkeypatch, headers=headers, trusted=trusted)

    gpgpubkeycheck.process()

    assert reporting.create_report.called == 0


def test_unexpected_key_is_reported(monkeypatch):
    """
    An installed key missing from TrustedGpgKeys is reported with its packager.
    """
    _setup(
        monkeypatch,
        headers=[
            _header(_RH_ARMOR),
            _header(_UNTRUSTED_ARMOR, name='gpg-pubkey-05707a62-68e6a1f3', packager=_UNTRUSTED_PACKAGER),
        ],
        trusted=[_RH_FP],
    )

    gpgpubkeycheck.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.report_fields
    assert report['title'] == _TITLE_UNEXPECTED
    assert report['severity'] == reporting.Severity.HIGH
    assert reporting.Groups.SECURITY in report['groups']

    summary = report['summary']
    assert _UNTRUSTED_FP in summary
    assert _UNTRUSTED_PACKAGER in summary
    # the trusted key must not be listed as unexpected
    assert _RH_FP not in summary


def test_keys_are_matched_by_full_fingerprint(monkeypatch):
    """
    A key sharing only its short key ID with a trusted key is still unexpected.

    This is the whole point of matching on the full fingerprint: the short key
    ID is 8 characters and is not collision resistant.
    """
    # the last 8 characters - the short key ID of a v4 key - are shared with _RH_FP
    trusted_with_same_short_keyid = 'f' * 32 + _RH_FP[32:]
    assert trusted_with_same_short_keyid != _RH_FP
    _setup(monkeypatch, headers=[_header(_RH_ARMOR)], trusted=[trusted_with_same_short_keyid])

    gpgpubkeycheck.process()

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == _TITLE_UNEXPECTED


@pytest.mark.parametrize('error_from_transaction_set', [True, False])
def test_rpm_query_failure_is_reported(monkeypatch, error_from_transaction_set):
    """
    A failing rpmdb query is reported as a query failure, not as a parsing failure.
    """
    error = rpm.error('cannot open Packages index')
    _setup(monkeypatch, trusted=[_RH_FP], rpm_error=error)
    if error_from_transaction_set:
        # the actor wraps both the TransactionSet() and the dbMatch() call
        def failing_transaction_set():
            raise error

        monkeypatch.setattr(gpgpubkeycheck.rpm, 'TransactionSet', failing_transaction_set)

    gpgpubkeycheck.process()

    _assert_cannot_check_report('querying the RPM DB')
    assert any('Failed to run rpm query' in msg for msg in api.current_logger.errmsg)


@pytest.mark.parametrize('bad_armor', [
    # the underlying tool could not read the armor at all
    _BROKEN_ARMOR,
    # a gpg-pubkey is expected to hold exactly one key; anything else is not understood
    _TWO_KEYS_ARMOR,
])
def test_unparseable_key_is_reported(monkeypatch, bad_armor):
    _setup(monkeypatch, headers=[_header(bad_armor)], trusted=[_RH_FP])

    gpgpubkeycheck.process()

    _assert_cannot_check_report('parsing of the keys')


def test_unparseable_key_suppresses_the_unexpected_key_check(monkeypatch):
    """
    One unreadable key means the whole check is inconclusive.

    The unexpected key present here is deliberately NOT reported: with a key we
    could not read, the actor cannot claim to know what is installed, so it asks
    for a complete manual verification instead of a partial answer.
    """
    _setup(
        monkeypatch,
        headers=[_header(_BROKEN_ARMOR), _header(_UNTRUSTED_ARMOR, packager=_UNTRUSTED_PACKAGER)],
        trusted=[_RH_FP],
    )

    gpgpubkeycheck.process()

    # the single 'cannot check' report asserted here is the only one produced; the
    # unexpected key is not named anywhere, the user is asked to verify all of them
    _assert_cannot_check_report('parsing of the keys')
    assert _UNTRUSTED_FP not in reporting.create_report.report_fields['summary']


def test_missing_trusted_keys_message_is_reported(monkeypatch):
    """
    Without TrustedGpgKeys there is nothing to compare against, so the installed keys are listed.
    """
    _setup(
        monkeypatch,
        headers=[_header(_RH_ARMOR), _header(_UNTRUSTED_ARMOR, packager=_UNTRUSTED_PACKAGER)],
        trusted=None,
    )

    gpgpubkeycheck.process()

    _assert_cannot_check_report('missing facts')
    summary = reporting.create_report.report_fields['summary']
    # every installed key is listed with its packager, so the user can check them by hand
    for fingerprint, packager in ((_RH_FP, _RH_PACKAGER), (_UNTRUSTED_FP, _UNTRUSTED_PACKAGER)):
        assert fingerprint in summary
        assert packager in summary


def test_get_installed_fps_tuple_pairs_fingerprint_with_packager(monkeypatch):
    """
    The full fingerprint comes from the parsed armor, the packager from the rpm header.
    """
    _setup(
        monkeypatch,
        headers=[
            _header(_RH_ARMOR),
            _header(_UNTRUSTED_ARMOR, packager=_UNTRUSTED_PACKAGER),
            _header(_BROKEN_ARMOR, name='gpg-pubkey-deadbeef-00000000'),
        ],
        trusted=[],
    )

    installed_fps_tuples, failed_to_process = gpgpubkeycheck._get_installed_fps_tuple()

    assert installed_fps_tuples == [(_RH_FP, _RH_PACKAGER), (_UNTRUSTED_FP, _UNTRUSTED_PACKAGER)]
    # the unreadable key is reported by its rpm name, the only thing known about it
    assert failed_to_process == ['gpg-pubkey-deadbeef-00000000']
