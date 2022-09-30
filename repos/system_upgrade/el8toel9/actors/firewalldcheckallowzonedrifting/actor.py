from leapp import reporting
from leapp.actors import Actor
from leapp.models import FirewalldGlobalConfig, FirewallsFacts
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class FirewalldCheckAllowZoneDrifting(Actor):
    """
    This actor will check if AllowZoneDrifiting=yes in firewalld.conf. This
    option has been removed in RHEL-9 and behavior is as if
    AllowZoneDrifiting=no.
    """

    name = 'firewalld_check_allow_zone_drifting'
    consumes = (FirewallsFacts, FirewalldGlobalConfig)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        # If firewalld is not enabled then don't bother the user about its
        # configuration. This Report keys off a _default_ value and as such
        # will trigger for all users that have not done one of the following:
        #   - disabled firewalld
        #   - manually set AllowZoneDrifting=no (as firewalld logs suggests)
        #
        for facts in self.consume(FirewallsFacts):
            if not facts.firewalld.enabled:
                return

        for facts in self.consume(FirewalldGlobalConfig):
            if not facts.allowzonedrifting:
                return

        create_report([
            reporting.Title('Firewalld Configuration AllowZoneDrifting Is Unsupported'),
            reporting.Summary('Firewalld has enabled configuration option '
                              '"{conf_key}" which has been removed in RHEL-9. '
                              'New behavior is as if "{conf_key}" was set to "no".'.format(
                                  conf_key='AllowZoneDrifiting')),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY, reporting.Groups.FIREWALL]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.ExternalLink(
                url='https://access.redhat.com/articles/4855631',
                title='Changes in firewalld related to Zone Drifting'),
            reporting.Remediation(
                hint='Set AllowZoneDrifting=no in /etc/firewalld/firewalld.conf',
                commands=[['sed', '-i', 's/^AllowZoneDrifting=.*/AllowZoneDrifting=no/',
                           '/etc/firewalld/firewalld.conf']]),
        ])
