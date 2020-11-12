from leapp.actors import Actor
from leapp.models import FirewalldFacts
from leapp.libraries.actor import private
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


related = [reporting.RelatedResource('package', 'firewalld')]


class CheckFirewalld(Actor):
    """
    Check for certain firewalld configuration that may prevent an upgrade.
    """

    name = 'check_firewalld'
    consumes = (FirewalldFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        unsupported_tables = []
        unsupported_ipset_types = []
        list_separator_fmt = '\n    -'
        for facts in self.consume(FirewalldFacts):
            for table in facts.ebtablesTablesInUse:
                if not private.isEbtablesTableSupported(table):
                    unsupported_tables.append(table)
            for ipset_type in facts.ipsetTypesInUse:
                if not private.isIpsetTypeSupportedByNftables(ipset_type):
                    unsupported_ipset_types.append(ipset_type)

        if unsupported_tables:
            format_tuple = (
                list_separator_fmt,
                list_separator_fmt.join(list(set(unsupported_tables))),)
            create_report([
                reporting.Title('Firewalld is using an unsupported ebtables table.'),
                reporting.Summary('ebtables in RHEL-8 does not support these tables:{}{}'.format(*format_tuple)),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([
                        reporting.Groups.FIREWALL,
                        reporting.Groups.SECURITY,
                        reporting.Groups.NETWORK,
                        reporting.Groups.INHIBITOR
                ]),
                reporting.Remediation(
                    hint='Remove firewalld direct rules that use these ebtables tables:{}{}'.format(*format_tuple)
                )
            ] + related)

        if unsupported_ipset_types:
            format_tuple = (
                list_separator_fmt,
                list_separator_fmt.join(list(set(unsupported_ipset_types))),)
            create_report([
                reporting.Title('Firewalld is using an unsupported ipset type.'),
                reporting.Summary(
                    'These ipset types are not supported by firewalld\'s nftables backend:{}{}'.format(*format_tuple)
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([
                        reporting.Groups.FIREWALL,
                        reporting.Groups.SECURITY,
                        reporting.Groups.NETWORK,
                        reporting.Groups.INHIBITOR
                ]),
                reporting.Remediation(
                    hint='Remove ipsets of these types from firewalld:{}{}'.format(*format_tuple)
                )
            ] + related)
