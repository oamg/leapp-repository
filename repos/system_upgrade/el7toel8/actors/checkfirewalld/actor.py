from leapp.actors import Actor
from leapp.models import FirewalldFacts
from leapp.libraries.actor import private
from leapp.libraries.common.reporting import report_with_remediation
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


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
            report_with_remediation(
                title='Firewalld is using an unsupported ebtables table.',
                summary='ebtables in RHEL-8 does not support these tables:{}{}'.format(*format_tuple),
                remediation='Remove firewalld direct rules that use these ebtables tables:{}{}'.format(*format_tuple),
                severity='high',
                flags=['inhibitor'])
        if unsupported_ipset_types:
            format_tuple = (
                list_separator_fmt,
                list_separator_fmt.join(list(set(unsupported_ipset_types))),)
            report_with_remediation(
                title='Firewalld is using an unsupported ipset type.',
                summary='These ipset types are not supported by firewalld\'s nftables backend:{}{}'.format(
                    *format_tuple),
                remediation='Remove ipsets of these types from firewalld:{}{}'.format(*format_tuple),
                severity='high',
                flags=['inhibitor'])
