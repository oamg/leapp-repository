from leapp import reporting
from leapp.libraries.actor import trustedgpgkeydircheck
from leapp.libraries.common.gpg import GpgKeyInfo
from leapp.libraries.common.testutils import create_report_mocked, logger_mocked
from leapp.libraries.stdlib import api


def _v4(short_keyid):
    return GpgKeyInfo(fingerprint=short_keyid * 5, short_keyid=short_keyid, is_pqc=False)


def _v6(short_keyid):
    return GpgKeyInfo(fingerprint=short_keyid * 8, short_keyid=short_keyid, is_pqc=True)


def _setup(monkeypatch, keyfiles, nogpgcheck=False):
    # keyfiles: {path: [GpgKeyInfo, ...]}
    monkeypatch.setattr(trustedgpgkeydircheck, 'is_nogpgcheck_set', lambda: nogpgcheck)
    monkeypatch.setattr(trustedgpgkeydircheck, 'get_path_to_gpg_certs', lambda: '/trust')
    monkeypatch.setattr(
        trustedgpgkeydircheck, 'iter_gpg_keyfiles',
        lambda root_dir, include_pqc: iter(keyfiles.keys())
    )
    monkeypatch.setattr(trustedgpgkeydircheck, 'parse_gpg_key_from_file', lambda path: keyfiles[path])
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())


def test_nogpgcheck_skips(monkeypatch):
    _setup(monkeypatch, {'/trust/misplaced': [_v6('05707a62')]}, nogpgcheck=True)
    trustedgpgkeydircheck.process()
    assert reporting.create_report.called == 0


def test_only_v4_keys_no_report(monkeypatch):
    _setup(monkeypatch, {'/trust/a': [_v4('fd431d51')], '/trust/b': [_v4('199e2f91')]})
    trustedgpgkeydircheck.process()
    assert reporting.create_report.called == 0


def test_v6_key_in_root_inhibits(monkeypatch):
    _setup(monkeypatch, {'/trust/a': [_v4('fd431d51')], '/trust/pqc-key': [_v6('05707a62')]})
    trustedgpgkeydircheck.process()
    assert reporting.create_report.called == 1
    report = reporting.create_report.report_fields
    assert reporting.Groups.INHIBITOR in report['groups']
    assert '/trust/pqc-key' in report['summary']
    assert '05707a62' in report['summary']
    assert '/trust/a' not in report['summary']


def test_mixed_keyfile_lists_only_v6_ids(monkeypatch):
    _setup(monkeypatch, {'/trust/mixed': [_v4('fd431d51'), _v6('05707a62')]})
    trustedgpgkeydircheck.process()
    assert reporting.create_report.called == 1
    summary = reporting.create_report.report_fields['summary']
    assert '/trust/mixed' in summary
    assert '05707a62' in summary
    # only the misplaced v6 key is reported, not the correctly placed v4 one
    assert 'fd431d51' not in summary
