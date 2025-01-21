import os

from leapp import reporting
from leapp.actors import Actor
from leapp.models import IfCfg, NetworkManagerConfig, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNetworkDeprecations9to10(Actor):
    """
    Ensures that network configuration doesn't rely on unsupported settings

    Inhibits upgrade if the network configuration includes settings that
    could possibly not work on the upgraded system.

    Includes check for dhclient DHCP plugin that will be removed from RHEL10.
    """

    name = "network_deprecations"
    consumes = (NetworkManagerConfig, IfCfg,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    @staticmethod
    def report_dhclient():
        title = 'Deprecated DHCP plugin configured'
        summary = ('NetworkManager is configured to use the "dhclient" DHCP module.'
                   ' In Red Hat Enterprise Linux 10, this setting will be ignored'
                   ' along with any dhcp-client specific configuration.')
        remediation = ('Remove "dhcp=dhclient" line from "[main]" section from all'
                       ' configuration files in "/etc/NetworkManager". Review'
                       ' configuration in "/etc/dhcp", which will be ignored.')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Remediation(hint=remediation),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.RelatedResource('package', 'dhcp-client'),
            reporting.RelatedResource('package', 'NetworkManager'),
        ])

    @staticmethod
    def report_ifcfg_rules(conn):
        reporting.create_report([
            reporting.Title('Legacy network configuration with policy routing rules found'),
            reporting.Summary('Network configuration files in "ifcfg" format is present accompanied'
                              ' by legacy routing rules. In Red Hat Enterprise Linux 10, support'
                              ' for these files is no longer enabled and the configuration will be'
                              ' ignored. Legacy routing rules are not supported by NetworkManager'
                              ' natively and therefore can not be migrated automatically.'),
            reporting.Remediation(hint='Replace the routing rules with equivalent'
                                       ' "ipv4.routing-rules" or "ipv6.routing-rules" properties,'
                                       ' then migrate the connection with "nmcli conn migrate"'),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/7083803',
                title='How to migrate the connection from ifcfg to NetworkManager keyfile plugin?'),
            reporting.ExternalLink(
                url='https://networkmanager.dev/docs/api/latest/nmcli.html',
                title='nmcli(1) manual, describes "connection migrate" sub-command.'),
            reporting.ExternalLink(
                url='https://networkmanager.dev/docs/api/latest/nm-settings-ifcfg-rh.html',
                title='nm-settings-ifcfg-rh(5), description of the "ifcfg" format'),
            reporting.ExternalLink(
                url='https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html',
                title='nm-settings-keyfile(5), description of the "keyfile" format'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.RelatedResource('package', 'NetworkManager'),
            reporting.RelatedResource('package', 'NetworkManager-dispatcher-routing-rules'),
        ] + [reporting.RelatedResource('file', file) for file in conn.values()])
        pass

    @staticmethod
    def report_ifcfg_leftover(conn):
        reporting.create_report([
            reporting.Title('Unused legacy network configuration found'),
            reporting.Summary('Files that used to accompany legacy network configuration in "ifcfg"'
                              ' format are present, even though the configuration itself is not'
                              ' longer there. These files will be ignored.'),
            reporting.Remediation(hint='Verify that the files were not left behind by incomplete'
                                       ' migration, fix up configuration if necessary, and remove'
                                       ' them.'),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/7083803',
                title='How to migrate the connection from ifcfg to NetworkManager keyfile plugin?'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
        ] + [reporting.RelatedResource('file', file) for file in conn.values()])

    @staticmethod
    def report_ifcfg(conn):
        reporting.create_report([
            reporting.Title('Legacy network configuration found'),
            reporting.Summary('Network configuration file in legacy "ifcfg" format is present.'
                              ' In Red Hat Enterprise Linux 10, support for these files is no longer'
                              ' enabled and the configuration will be ignored.'),
            reporting.Remediation(
                hint='Convert the configuration into NetworkManager native "keyfile" format.',
                commands=[['nmcli', 'connection', 'migrate', conn['ifcfg']]]),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/7083803',
                title='How to migrate the connection from ifcfg to NetworkManager keyfile plugin?'),
            reporting.ExternalLink(
                url='https://networkmanager.dev/docs/api/latest/nmcli.html',
                title='nmcli(1) manual, describes "connection migrate" sub-command.'),
            reporting.ExternalLink(
                url='https://networkmanager.dev/docs/api/latest/nm-settings-ifcfg-rh.html',
                title='nm-settings-ifcfg-rh(5), description of the "ifcfg" format'),
            reporting.ExternalLink(
                url='https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html',
                title='nm-settings-keyfile(5), description of the "keyfile" format'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.RelatedResource('package', 'NetworkManager'),
        ] + [reporting.RelatedResource('file', file) for file in conn.values()])

    def process(self):
        for nm_config in self.consume(NetworkManagerConfig):
            self.log.info('Consuming dhcp={}'.format(nm_config.dhcp))
            if nm_config.dhcp == 'dhclient':
                CheckNetworkDeprecations9to10.report_dhclient()

        conns = {}

        for ifcfg in self.consume(IfCfg):
            self.log.info('Consuming ifcfg={}'.format(ifcfg.filename))
            rule_basename = os.path.basename(ifcfg.filename)
            (kind, name) = rule_basename.split('-', 1)
            if name not in conns:
                conns[name] = {}
            conns[name][kind] = ifcfg.filename

        for name in conns:
            conn = conns[name]
            if 'ifcfg' in conn:
                if 'rule' in conn or 'rule6' in conn:
                    CheckNetworkDeprecations9to10.report_ifcfg_rules(conn)
                else:
                    CheckNetworkDeprecations9to10.report_ifcfg(conn)
            else:
                CheckNetworkDeprecations9to10.report_ifcfg_leftover(conn)
