from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api, format_list
from leapp.models import PostfixBdbConfiguration

REPORT_KCS_URL = 'https://access.redhat.com/solutions/7131247'


def process():
    msg = next(api.consume(PostfixBdbConfiguration), None)
    if not msg:
        raise StopActorExecutionError('Expected PostfixBdbConfiguration, but got None')

    if not msg.postfix_present:
        api.current_logger().debug('postfix package not found, no report generated')
        return

    if not msg.bdb_occurrences:
        api.current_logger().debug(
            'Postfix is installed but no hash:/btree: maps were found; no report generated'
        )
        return

    summary = (
        'RHEL 10 no longer provides Berkeley DB, so Postfix cannot use the '
        'hash: or btree: lookup table types after the upgrade. Postfix will '
        'fail to start or to rebuild aliases (unsupported dictionary type: hash) '
        'until the maps are converted to lmdb. '
        'The following configuration entries still use a Berkeley DB map type:'
        '{occurrences}'
    ).format(
        occurrences=format_list(msg.bdb_occurrences, callback_sort=None),
    )

    hint = (
        'Do not rely on Leapp to rewrite Postfix configuration. Before or after '
        'the upgrade, replace hash: and btree: with lmdb: in /etc/postfix/main.cf '
        '(and related files), set default_database_type = lmdb, and rebuild maps '
        'with postmap/postalias. See the linked article for the full procedure. '
        'Target system: {target_distro} 10.'
    ).format_map(DISTRO_REPORT_NAMES)

    reporting.create_report([
        reporting.Title(
            'Postfix Berkeley DB (hash/btree) maps are not available after the upgrade'
        ),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(
            title='Postfix fails with unsupported dictionary type: hash after upgrading to RHEL 10',
            url=REPORT_KCS_URL,
        ),
        reporting.RelatedResource('package', 'postfix'),
        reporting.RelatedResource('file', '/etc/postfix/main.cf'),
        reporting.Remediation(hint=hint),
    ])
