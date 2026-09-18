import pytest

from leapp import reporting
from leapp.libraries.actor import trustedgpgkeydircheck
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import GpgKey, MisplacedTrustedGpgKeys

_TRUSTED_DIR = '/etc/leapp/files/distro/rhel/rpm-gpg/10'
_PQC_DIR = _TRUSTED_DIR + '/pqc'

# headers of the two sections of the report; only the relevant ones are included
_PQC_SECTION = 'Post-quantum keys found in'
_CLASSIC_SECTION = 'Standard keys found in'


def _key(filename, short_keyid):
    return GpgKey(fingerprint=short_keyid, rpmdb=False, filename=filename)


_MISPLACED_PQC = _key(_TRUSTED_DIR + '/RPM-GPG-KEY-pqc-redhat-release', '05707a62')
_MISPLACED_CLASSIC = _key(_PQC_DIR + '/RPM-GPG-KEY-redhat-release', 'fd431d51')


def _setup(monkeypatch, msgs, nogpgcheck=False):
    envars = {'LEAPP_NOGPGCHECK': '1'} if nogpgcheck else None
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars=envars, msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(trustedgpgkeydircheck, 'get_path_to_gpg_certs', lambda: _TRUSTED_DIR)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())


def test_nogpgcheck_skips_check(monkeypatch):
    """
    With --nogpgcheck nothing is reported even though misplaced keys were found.
    """
    msgs = [MisplacedTrustedGpgKeys(pqc_keys=[_MISPLACED_PQC], classic_keys=[_MISPLACED_CLASSIC])]
    _setup(monkeypatch, msgs, nogpgcheck=True)

    trustedgpgkeydircheck.process()

    assert reporting.create_report.called == 0
    assert any('--nogpgcheck option is used' in msg for msg in api.current_logger.dbgmsg)


def test_no_message_no_report(monkeypatch):
    """
    Nothing is reported when the scanner did not produce the message at all (source < 9.9).
    """
    _setup(monkeypatch, [])

    trustedgpgkeydircheck.process()

    assert reporting.create_report.called == 0
    assert any('No MisplacedTrustedGpgKeys received' in msg for msg in api.current_logger.dbgmsg)


def test_no_misplaced_keys_no_report(monkeypatch):
    """
    Nothing is reported when the message carries no misplaced keys.
    """
    _setup(monkeypatch, [MisplacedTrustedGpgKeys()])

    trustedgpgkeydircheck.process()

    assert reporting.create_report.called == 0
    assert any('No misplaced keys detected' in msg for msg in api.current_logger.dbgmsg)


@pytest.mark.parametrize('pqc_keys, classic_keys, expected_sections', [
    # a post-quantum key at the top-level is reported in the post-quantum section only
    ([_MISPLACED_PQC], [], [_PQC_SECTION]),
    # a standard key in the 'pqc' subdirectory is reported in the standard section only
    ([], [_MISPLACED_CLASSIC], [_CLASSIC_SECTION]),
    # both kinds of misplaced keys are reported in a single report
    ([_MISPLACED_PQC], [_MISPLACED_CLASSIC], [_PQC_SECTION, _CLASSIC_SECTION]),
])
def test_misplaced_keys_inhibit(monkeypatch, pqc_keys, classic_keys, expected_sections):
    """
    Misplaced keys inhibit the upgrade and only the relevant sections are in the report.
    """
    _setup(monkeypatch, [MisplacedTrustedGpgKeys(pqc_keys=pqc_keys, classic_keys=classic_keys)])

    trustedgpgkeydircheck.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.report_fields
    assert reporting.Groups.INHIBITOR in report['groups']
    assert report['severity'] == reporting.Severity.HIGH

    summary = report['summary']
    for section in (_PQC_SECTION, _CLASSIC_SECTION):
        assert (section in summary) == (section in expected_sections)

    # the keyfiles are referenced by their basename, together with the key IDs they contain
    for key in pqc_keys + classic_keys:
        assert 'RPM-GPG-KEY' in summary
        assert key.fingerprint in summary

    # the user is told where each of the key types belongs and how to fix the layout
    assert _TRUSTED_DIR in summary
    assert _PQC_DIR in summary
    hint = report['detail']['remediations'][0]['context']
    assert 'sq packet dump' in hint


def test_report_groups_keys_by_keyfile(monkeypatch):
    """
    Keys from the same keyfile are reported as a single entry listing all their key IDs.
    """
    keyfile = _TRUSTED_DIR + '/RPM-GPG-KEY-pqc-redhat-release'
    other_keyfile = _TRUSTED_DIR + '/RPM-GPG-KEY-pqc-custom'
    pqc_keys = [
        _key(keyfile, '05707a62'),
        _key(keyfile, '199e2f91'),
        _key(other_keyfile, 'b2973cf6'),
    ]
    _setup(monkeypatch, [MisplacedTrustedGpgKeys(pqc_keys=pqc_keys)])

    trustedgpgkeydircheck.process()

    assert reporting.create_report.called == 1
    summary = reporting.create_report.report_fields['summary']
    assert 'RPM-GPG-KEY-pqc-redhat-release (key IDs: 05707a62, 199e2f91)' in summary
    assert 'RPM-GPG-KEY-pqc-custom (key IDs: b2973cf6)' in summary
