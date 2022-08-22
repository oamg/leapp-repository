from leapp.actors import Actor
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckPostfix(Actor):
    """
    Check if postfix is installed, check whether configuration update is needed.
    """

    name = 'check_postfix'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for fact in self.consume(InstalledRedHatSignedRPM):
            for rpm in fact.items:
                if rpm.name == 'postfix':
                    create_report([
                        reporting.Title('Postfix has incompatible changes in the next major version'),
                        reporting.Summary(
                            'Postfix 3.x has so called "compatibility safety net" that runs Postfix programs '
                            'with backwards-compatible default settings. It will log a warning whenever '
                            'backwards-compatible default setting may be required for continuity of service. '
                            'Based on this logging the system administrator can decide if any '
                            'backwards-compatible settings need to be made permanent in main.cf or master.cf, '
                            'before turning off the backwards-compatibility safety net.\n'
                            'The backward compatibility safety net is by default turned off in Red Hat '
                            'Enterprise Linux 8.\n'
                            'It can be turned on by running:  "postconf -e compatibility_level=0\n'
                            'It can be turned off by running: "postconf -e compatibility_level=2\n\n'
                            'In the Postfix MySQL database client, the default "option_group" value has changed '
                            'to "client", i.e. it now reads options from the [client] group from the MySQL '
                            'configuration file. To disable it, set "option_group" to the empty string.\n\n'
                            'The postqueue command no longer forces all message arrival times to be reported '
                            'in UTC. To get the old behavior, set TZ=UTC in main.cf:import_environment.\n\n'
                            'Postfix 3.2 enables elliptic curve negotiation. This changes the default '
                            'smtpd_tls_eecdh_grade setting to "auto", and introduces a new parameter '
                            '"tls_eecdh_auto_curves" with the names of curves that may be negotiated.\n\n'
                            'The "master.cf" chroot default value has changed from "y" (yes) to "n" (no). '
                            'This applies to master.cf services where chroot field is not explicitly '
                            'specified.\n\n'
                            'The "append_dot_mydomain" default value has changed from "yes" to "no". You may '
                            'need changing it to "yes" if senders cannot use complete domain names in e-mail '
                            'addresses.\n\n'
                            'The "relay_domains" default value has changed from "$mydestination" to the empty '
                            'value. This could result in unexpected "Relay access denied" errors or ETRN errors, '
                            'because now will postfix by default relay only for the localhost.\n\n'
                            'The "mynetworks_style" default value has changed from "subnet" to "host". '
                            'This parameter is used to implement the "permit_mynetworks" feature. The change '
                            'could result in unexpected "access denied" errors, because postfix will now by '
                            'default trust only the local machine, not the remote SMTP clients on the '
                            'same IP subnetwork.\n\n'
                            'Postfix now supports dynamically loaded database plugins. Plugins are shipped '
                            'in individual RPM sub-packages. Correct database plugins have to be installed, '
                            'otherwise the specific database client will not work. For example for PostgreSQL '
                            'map to work, the postfix-pgsql RPM package has to be installed.\n',
                        ),
                        reporting.Severity(reporting.Severity.LOW),
                        reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.EMAIL]),
                        reporting.RelatedResource('package', 'postfix')
                    ])
                    return
