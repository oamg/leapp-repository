from leapp.actors import Actor
from leapp.libraries.actor import vsftpdconfigupdate
from leapp.models import VsftpdFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class VsftpdConfigUpdate(Actor):
    """
    Modifies vsftpd configuration files on the target RHEL-8 system so that the effective
    configuration is the same, where possible. This means doing two things:
    1. Reverting the default configuration file (/etc/vsftpd/vsftpd.conf) to its state
       before the upgrade (where it makes sense), if the configuration file was being used
       with its default content (i.e., unmodified) on the source system (the configuration
       file gets replaced with a new version during the RPM upgrade in this case).
       The anonymous_enable option falls in this category.
    2. Adding 'option=old_effective_value' to configuration files for options whose default
       value has changed, if the option is not explicitly specified in the configuration file.
       The strict_ssl_read_eof option falls in this category.
    3. Disabling options that cannot be enabled, otherwise vsftpd wouldn't work.
       The tcp_wrappers option falls in this category.
    """

    name = 'vsftpd_config_update'
    consumes = (VsftpdFacts,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        try:
            vsftpd_facts = next(self.consume(VsftpdFacts))
        except StopIteration:
            return
        vsftpdconfigupdate.migrate_configs(vsftpd_facts)
