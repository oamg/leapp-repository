# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
from leapp.actors import Actor
from leapp.libraries.actor.openldap import process as ol_process
from leapp.libraries.actor.sssd import process as sd_process
from leapp import reporting
from leapp.reporting import Report, create_report
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class OpenldapNSStoOpenSSL(Actor):
    """
    Convert old NSS-style TLS configuration to the new OpenSSL-style configuration.

    Configuration in /etc/openldap/ldap.conf will be converted into
    OpenSSL-style configuration if necessary. The converted certificates
    will be placed into /etc/openldap/certs-migrated and ldap.conf will be
    updated with configuration pointing to extracted certificates. Similar
    process will occur for SSSD where certificates configuration is expected.
    """
    name = 'openldap_nss_to_openssl'
    produces = (Report,)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        if not self.handle_errors(ol_process, self.abandon, self.fail):
            self.fail('OpenLDAP certificates were not properly converted.')
        if not self.handle_errors(sd_process, self.abandon, self.fail):
            self.fail('SSSD configuration of OpenLDAP certificates was not properly converted.')

    def handle_errors(self, process, abandon, fail):
        rv, err = process(self.log)
        if rv is None:
            abandon(err)
            return False
        elif rv is False:
            fail(err)
            return False
        elif rv is True:
            self.success()
            return True
        fail('Unexpected error occurred: %s' % err)
        return False

    def abandon(self, reason):
        create_report([reporting.Title('No OpenLDAP certificates conversion necessary'),
                       reporting.Summary('%s. Certificates are most likely in correct format.'
                                         ' Leaving as is.' % reason),
                       reporting.Severity(reporting.Severity.LOW)])

    def success(self):
        create_report([reporting.Title('OpenLDAP certificates converted successfully'),
                       reporting.Summary('Created PEM certificates and updated the configuration file.'),
                       reporting.Severity(reporting.Severity.LOW)])

    def fail(self, err):
        create_report([reporting.Title('OpenLDAP certificates processing failed'),
                       reporting.Summary(str(err)),
                       reporting.Severity(reporting.Severity.HIGH)])
