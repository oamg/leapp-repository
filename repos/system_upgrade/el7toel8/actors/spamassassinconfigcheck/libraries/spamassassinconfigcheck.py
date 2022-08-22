from leapp import reporting
from leapp.libraries.common.spamassassinutils import \
    SPAMC_CONFIG_FILE, SPAMASSASSIN_SERVICE_OVERRIDE, SYSCONFIG_SPAMASSASSIN


def _check_spamc_config(facts, report_func):
    title = ('spamc no longer allows specifying the TLS version and no longer '
             'supports SSLv3')
    summary_generic = ('spamc no longer allows using the "--ssl" option with an '
                       'argument specifying the TLS version - the option can only '
                       'be used without an argument. Also, spamc no longer supports '
                       'SSLv3.')
    if facts.spamc_ssl_argument:
        summary_detail = ('The spamc configuration file uses "--ssl %s", it will '
                          'be updated during the upgrade.'
                          % facts.spamc_ssl_argument)
        summary = reporting.Summary('%s %s' % (summary_generic, summary_detail))
        resource = reporting.RelatedResource('file', SPAMC_CONFIG_FILE)
    else:
        summary = reporting.Summary(summary_generic)
        resource = None
    severity = (reporting.Severity.HIGH if facts.spamc_ssl_argument == 'sslv3'
                else reporting.Severity.MEDIUM)
    hint = 'Please update your scripts and configuration, if there are any.'

    args = [
        reporting.Title(title),
        summary,
        reporting.Groups([reporting.Groups.ENCRYPTION]),
        reporting.Severity(severity),
        reporting.Remediation(hint=hint),
    ]
    if resource:
        args.append(resource)
    report_func(args)


def _check_spamd_config_ssl(facts, report_func):
    title = ('spamd no longer allows specifying the TLS version and no longer '
             'supports SSLv3')
    summary_generic = ('spamd no longer accepts the --ssl-version option and '
                       'no longer supports SSLv3.')
    if facts.spamd_ssl_version:
        summary_detail = ('The spamd sysconfig file uses "--ssl-version %s", '
                          'it will be updated during the upgrade.'
                          % facts.spamd_ssl_version)
        summary = reporting.Summary('%s %s' % (summary_generic, summary_detail))
        resource = reporting.RelatedResource('file', SYSCONFIG_SPAMASSASSIN)
    else:
        summary = reporting.Summary(summary_generic)
        resource = None
    severity = (reporting.Severity.HIGH if facts.spamd_ssl_version == 'sslv3'
                else reporting.Severity.MEDIUM)
    hint = 'Please update your scripts and configuration, if there are any.'

    args = [
        reporting.Title(title),
        summary,
        reporting.Groups([reporting.Groups.ENCRYPTION, reporting.Groups.SERVICES]),
        reporting.Severity(severity),
        reporting.Remediation(hint=hint)
    ]
    if resource:
        args.append(resource)
    report_func(args)


def _check_spamd_config_service_type(facts, report_func):
    title = 'The type of the spamassassin systemd service has changed'
    summary_generic = 'The type of spamassassin.service has been changed from "forking" to "simple".'
    if facts.service_overriden:
        summary_detail = 'However, the service appears to be overriden; no migration action will occur.'
        resource = reporting.RelatedResource('file', SPAMASSASSIN_SERVICE_OVERRIDE)
    else:
        summary_detail = 'The spamassassin sysconfig file will be updated.'
        resource = reporting.RelatedResource('file', SYSCONFIG_SPAMASSASSIN)
    report_func([
        reporting.Title(title),
        reporting.Summary('%s %s' % (summary_generic, summary_detail)),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.Severity(reporting.Severity.MEDIUM),
        resource
    ])


def _report_sa_update_change(report_func):
    summary = ('sa-update no longer supports SHA1 validation of filtering rules, '
               'SHA256/SHA512 validation is done instead. This may affect you if '
               'you are using an alternative update channel (sa-update used with '
               'option --channel or --channelfile), or if you install filtering '
               'rule updates directly from files (sa-update --install).')
    report_func([reporting.Title('sa-update no longer supports SHA1 validation'),
                 reporting.Summary(summary),
                 reporting.Severity(reporting.Severity.LOW)])


def produce_reports(facts):
    """
    Checks spamassassin configuration and produces reports.
    """
    _check_spamc_config(facts, reporting.create_report)
    _check_spamd_config_ssl(facts, reporting.create_report)
    _check_spamd_config_service_type(facts, reporting.create_report)
    _report_sa_update_change(reporting.create_report)
