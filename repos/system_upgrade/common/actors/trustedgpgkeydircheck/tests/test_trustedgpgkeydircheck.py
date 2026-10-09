import pytest

from leapp import reporting
from leapp.libraries.actor import trustedgpgkeydircheck
from leapp.libraries.common.gpg import GpgKeyInfo
from leapp.libraries.common.testutils import create_report_mocked

_TRUST_DIR = '/trust'
_PQC_PREFIX = '/trust/pqc/'


def _v4(short_keyid):
    return GpgKeyInfo(fingerprint=short_keyid * 5, short_keyid=short_keyid, is_pqc=False)


def _v6(short_keyid):
    return GpgKeyInfo(fingerprint=short_keyid * 8, short_keyid=short_keyid, is_pqc=True)


def _setup(monkeypatch, keyfiles, nogpgcheck=False):
    # keyfiles: {path: [GpgKeyInfo, ...]}; paths under _PQC_PREFIX live in the 'pqc' subfolder
    monkeypatch.setattr(trustedgpgkeydircheck, 'is_nogpgcheck_set', lambda: nogpgcheck)
    monkeypatch.setattr(trustedgpgkeydircheck, 'get_path_to_gpg_certs', lambda: _TRUST_DIR)

    def iter_gpg_keyfiles_mocked(root_dir, include_pqc):
        # mirror the real iter_gpg_keyfiles: skip the 'pqc' subfolder unless include_pqc
        for path in keyfiles:
            if not include_pqc and path.startswith(_PQC_PREFIX):
                continue
            yield path

    monkeypatch.setattr(trustedgpgkeydircheck, 'iter_gpg_keyfiles', iter_gpg_keyfiles_mocked)
    monkeypatch.setattr(trustedgpgkeydircheck, 'parse_gpg_key_from_file', lambda path: keyfiles[path])
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())


def test_nogpgcheck_skips(monkeypatch):
    _setup(monkeypatch, {'/trust/misplaced': [_v6('05707a62')]}, nogpgcheck=True)
    trustedgpgkeydircheck.process()
    assert reporting.create_report.called == 0


@pytest.mark.parametrize('keyfiles', [
    # only standard (v4) keys at the top-level
    {'/trust/standard-key': [_v4('fd431d51')], '/trust/standard-key-2': [_v4('199e2f91')]},
    # standard (v4) keys at the top-level and pqc (v6) keys in the 'pqc' subfolder
    {'/trust/standard-key': [_v4('fd431d51')], '/trust/pqc/pqc-key': [_v6('05707a62')]},
])
def test_correct_layout_no_report(monkeypatch, keyfiles):
    _setup(monkeypatch, keyfiles)
    trustedgpgkeydircheck.process()
    assert reporting.create_report.called == 0


@pytest.mark.parametrize('keyfiles, present, absent', [
    # a pqc (v6) key misplaced at the top-level inhibits; the correct standard key is not reported
    (
        {'/trust/standard-key': [_v4('fd431d51')], '/trust/misplaced': [_v6('05707a62')]},
        ['/trust/misplaced', '05707a62'],
        ['/trust/standard-key'],
    ),
    # a mixed keyfile at the top-level reports only its misplaced pqc (v6) key
    (
        {'/trust/mixed': [_v4('fd431d51'), _v6('05707a62')]},
        ['/trust/mixed', '05707a62'],
        ['fd431d51'],
    ),
    # a pqc (v6) key misplaced at the top-level still inhibits despite a correct 'pqc' subfolder
    (
        {
            '/trust/standard-key': [_v4('fd431d51')],
            '/trust/misplaced': [_v6('05707a62')],
            '/trust/pqc/pqc-key': [_v6('199e2f91')],
        },
        ['/trust/misplaced', '05707a62'],
        ['/trust/pqc/pqc-key', '199e2f91'],
    ),
    # a standard (v4) key misplaced in the 'pqc' subfolder inhibits; the correct standard key is not reported
    (
        {'/trust/standard-key': [_v4('fd431d51')], '/trust/pqc/misplaced': [_v4('199e2f91')]},
        ['/trust/pqc/misplaced', '199e2f91'],
        ['/trust/standard-key', 'fd431d51'],
    ),
    # a mixed keyfile in the 'pqc' subfolder reports only its misplaced standard (v4) key
    (
        {'/trust/pqc/mixed': [_v4('fd431d51'), _v6('05707a62')]},
        ['/trust/pqc/mixed', 'fd431d51'],
        ['05707a62'],
    ),
    # both a misplaced pqc key and a misplaced standard key are reported in a single report
    (
        {'/trust/misplaced': [_v6('05707a62')], '/trust/pqc/misplaced': [_v4('199e2f91')]},
        ['/trust/misplaced', '05707a62', '/trust/pqc/misplaced', '199e2f91'],
        [],
    ),
])
def test_misplaced_keys_inhibit(monkeypatch, keyfiles, present, absent):
    _setup(monkeypatch, keyfiles)
    trustedgpgkeydircheck.process()
    assert reporting.create_report.called == 1
    report = reporting.create_report.report_fields
    assert reporting.Groups.INHIBITOR in report['groups']
    summary = report['summary']
    for present_substring in present:
        assert present_substring in summary
    for absent_substring in absent:
        assert absent_substring not in summary
