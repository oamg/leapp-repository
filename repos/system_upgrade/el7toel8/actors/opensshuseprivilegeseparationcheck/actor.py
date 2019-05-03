from leapp.actors import Actor
from leapp.models import Report, OpenSshConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.common.reporting import report_generic


class OpenSshUsePrivilegeSeparationCheck(Actor):
    """
    UsePrivilegeSeparation configuration option was removed.

    Check the value of UsePrivilegeSeparation in OpenSSH server config file
    and warn about its deprecation if it is set to non-default value.
    """
    name = 'open_ssh_use_privilege_separation'
    consumes = (OpenSshConfig, )
    produces = (Report, )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for config in self.consume(OpenSshConfig):
            if config.use_privilege_separation is not None and \
               config.use_privilege_separation != "sandbox":
                report_generic(
                    title='OpenSSH configured not to use privilege separation sandbox',
                    summary='OpenSSH is configured to disable privilege '
                            'separation sandbox, which is decreasing security '
                            'and is no longer supported in RHEL 8',
                    severity='low')
