from leapp.libraries.actor import spamassassinconfigcheck
from leapp.libraries.common.testutils import create_report_mocked
from leapp.models import SpamassassinFacts


def test_check_spamc_config_tlsv1():
    facts = SpamassassinFacts(spamc_ssl_argument='tlsv1', service_overriden=False)
    report_func = create_report_mocked()

    spamassassinconfigcheck._check_spamc_config(facts, report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'specifying the TLS version' in report_fields['title']
    assert 'SSLv3' in report_fields['title']
    assert '--ssl' in report_fields['summary']
    assert 'SSLv3' in report_fields['summary']
    assert 'spamc configuration file' in report_fields['summary']
    assert '--ssl tlsv1' in report_fields['summary']
    assert all('update your scripts' in r['context'] for r in report_fields['detail']['remediations'])
    assert report_fields['severity'] == 'medium'


def test_check_spamc_config_sslv3():
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3', service_overriden=False)
    report_func = create_report_mocked()

    spamassassinconfigcheck._check_spamc_config(facts, report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'specifying the TLS version' in report_fields['title']
    assert 'SSLv3' in report_fields['title']
    assert '--ssl' in report_fields['summary']
    assert 'SSLv3' in report_fields['summary']
    assert 'spamc configuration file' in report_fields['summary']
    assert '--ssl sslv3' in report_fields['summary']
    assert all('update your scripts' in r['context'] for r in report_fields['detail']['remediations'])
    assert report_fields['severity'] == 'high'


def test_check_spamc_config_correct_config():
    facts = SpamassassinFacts(spamc_ssl_argument=None, service_overriden=False)
    report_func = create_report_mocked()

    spamassassinconfigcheck._check_spamc_config(facts, report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'specifying the TLS version' in report_fields['title']
    assert 'SSLv3' in report_fields['title']
    assert '--ssl' in report_fields['summary']
    assert 'SSLv3' in report_fields['summary']
    assert 'spamc configuration file' not in report_fields['summary']
    assert all('update your scripts' in r['context'] for r in report_fields['detail']['remediations'])
    assert report_fields['severity'] == 'medium'


def test_check_spamd_config_ssl_tlsv1():
    facts = SpamassassinFacts(spamd_ssl_version='tlsv1', service_overriden=False)
    report_func = create_report_mocked()

    spamassassinconfigcheck._check_spamd_config_ssl(facts, report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'specifying the TLS version' in report_fields['title']
    assert 'SSLv3' in report_fields['title']
    assert '--ssl-version' in report_fields['summary']
    assert 'SSLv3' in report_fields['summary']
    assert 'sysconfig' in report_fields['summary']
    assert '--ssl-version tlsv1' in report_fields['summary']
    assert all('update your scripts' in r['context'] for r in report_fields['detail']['remediations'])
    assert report_fields['severity'] == 'medium'


def test_check_spamd_config_ssl_sslv3():
    facts = SpamassassinFacts(spamd_ssl_version='sslv3', service_overriden=False)
    report_func = create_report_mocked()

    spamassassinconfigcheck._check_spamd_config_ssl(facts, report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'specifying the TLS version' in report_fields['title']
    assert 'SSLv3' in report_fields['title']
    assert '--ssl-version' in report_fields['summary']
    assert 'SSLv3' in report_fields['summary']
    assert 'sysconfig' in report_fields['summary']
    assert '--ssl-version sslv3' in report_fields['summary']
    assert all('update your scripts' in r['context'] for r in report_fields['detail']['remediations'])
    assert report_fields['severity'] == 'high'


def test_check_spamd_config_ssl_correct_config():
    facts = SpamassassinFacts(spamd_ssl_version=None, service_overriden=False)
    report_func = create_report_mocked()

    spamassassinconfigcheck._check_spamd_config_ssl(facts, report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'specifying the TLS version' in report_fields['title']
    assert 'SSLv3' in report_fields['title']
    assert '--ssl-version' in report_fields['summary']
    assert 'SSLv3' in report_fields['summary']
    assert 'sysconfig' not in report_fields['summary']
    assert all('update your scripts' in r['context'] for r in report_fields['detail']['remediations'])
    assert report_fields['severity'] == 'medium'


def test_check_spamd_config_service_type_service_overriden():
    facts = SpamassassinFacts(service_overriden=True)
    report_func = create_report_mocked()

    spamassassinconfigcheck._check_spamd_config_service_type(facts, report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'type of the spamassassin systemd service' in report_fields['title']
    assert 'The type of spamassassin.service' in report_fields['summary']
    assert 'overriden' in report_fields['summary']
    assert report_fields['severity'] == 'medium'


def test_check_spamd_config_service_type_service_not_overriden():
    facts = SpamassassinFacts(service_overriden=False)
    report_func = create_report_mocked()

    spamassassinconfigcheck._check_spamd_config_service_type(facts, report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'type of the spamassassin systemd service' in report_fields['title']
    assert 'The type of spamassassin.service' in report_fields['summary']
    assert 'will be updated' in report_fields['summary']
    assert report_fields['severity'] == 'medium'


def test_report_sa_update_change():
    report_func = create_report_mocked()

    spamassassinconfigcheck._report_sa_update_change(report_func)

    assert report_func.called == 1
    report_fields = report_func.report_fields
    assert 'sa-update no longer supports SHA1' in report_fields['title']
    assert 'no longer supports SHA1' in report_fields['summary']
    assert 'SHA256/SHA512' in report_fields['summary']
    assert '--channel or --channelfile' in report_fields['summary']
    assert '--install' in report_fields['summary']
    assert report_fields['severity'] == 'low'
