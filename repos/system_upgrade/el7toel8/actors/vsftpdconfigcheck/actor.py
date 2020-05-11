from leapp.actors import Actor
from leapp.libraries.actor import vsftpdconfigcheck
from leapp.models import TcpWrappersFacts, VsftpdFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class VsftpdConfigCheck(Actor):
    """
    Checks whether the vsftpd configuration is supported in RHEL-8. Namely checks that
    configuration files don't set tcp_wrappers=YES and vsftpd-related configuration is
    not present in tcp_wrappers configuration files at the same time.
    """

    name = 'vsftpd_config_check'
    consumes = (TcpWrappersFacts, VsftpdFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        try:
            vsftpd_facts = next(self.consume(VsftpdFacts))
        except StopIteration:
            return
        tcp_wrappers_facts = next(self.consume(TcpWrappersFacts))
        vsftpdconfigcheck.check_config_supported(tcp_wrappers_facts, vsftpd_facts)
