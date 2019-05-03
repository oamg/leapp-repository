from leapp.actors import Actor
from leapp.libraries.actor.library import semantics_changes
from leapp.models import Report, OpenSshConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.common.reporting import report_with_remediation


class OpenSshPermitRootLoginCheck(Actor):
    """
    OpenSSH no longer allows root logins with password.

    Check the values of PermitRootLogin in OpenSSH server configuration file
    and warn about potential issues after update.
    """
    name = 'openssh_permit_root_login'
    consumes = (OpenSshConfig, )
    produces = (Report, )
    tags = (ChecksPhaseTag, IPUWorkflowTag, )

    def process(self):
        for config in self.consume(OpenSshConfig):
            if len(config.permit_root_login) == 0:
                # TODO find out whether the file was modified and will be
                # replaced by the update. If so, this message is bogus
                report_with_remediation(
                    title='Possible problems with remote login using root account',
                    summary='OpenSSH configuration file does not explicitly state '
                            'the option PermitRootLogin in sshd_config file, '
                            'which will default in RHEL8 to "prohibit-password".',
                    remediation='If you depend on remote root logins using '
                                'passwords, condider setting up a different '
                                'user for remote administration or adding '
                                '"PermitRootLogin yes" to sshd_config.',
                    severity='high',
                    flags=['inhibitor'])

            # Check if there is at least one PermitRootLogin other than "no"
            # in match blocks (other than Match All).
            # This usually means some more complicated setup depending on the
            # default value being globally "yes" and being overwritten by this
            # match block
            if semantics_changes(config):
                report_with_remediation(
                    title='OpenSSH configured to allow root login',
                    summary='OpenSSH is configured to deny root logins in match '
                            'blocks, but not explicitly enabled in global or '
                            '"Match all" context. This update changes the '
                            'default to disable root logins using paswords '
                            'so your server migth get inaccessible.',
                    remediation='Consider using different user for administrative '
                                'logins or make sure your configration file '
                                'contains the line "PermitRootLogin yes" '
                                'in global context if desired.',
                    severity='high',
                    flags=['inhibitor'])
