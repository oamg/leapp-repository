from leapp.actors import Actor
from leapp.models import Report, OpenSshConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import api
from leapp.libraries.common.reporting import report_with_remediation


class OpenSshAlgorithmsCheck(Actor):
    """
    OpenSSH configuration does not contain any unsupported cryptographic algorithms.

    Check the values of Ciphers and MACs in OpenSSH server config file and warn
    about removed algorithms which might cause the server to fail to start.
    """
    name = 'open_ssh_algorithms'
    consumes = (OpenSshConfig,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        removed_ciphers = [
            "blowfish-cbc",
            "cast128-cbc",
            "arcfour",
            "arcfour128",
            "arcfour256",
        ]
        removed_macs = [
            "hmac-ripemd160",
        ]
        found_ciphers = []
        found_macs = []
        openssh_messages = self.consume(OpenSshConfig)
        config = next(openssh_messages)
        if list(openssh_messages):
            api.current_logger().warning('Unexpectedly received more than one OpenSshConfig message.')

        for cipher in removed_ciphers:
            if config.ciphers and cipher in config.ciphers:
                found_ciphers.append(cipher)
        for mac in removed_macs:
            if config.macs and mac in config.macs:
                found_macs.append(mac)

        if found_ciphers:
            report_with_remediation(
                title='OpenSSH configured to use removed ciphers',
                summary='OpenSSH is configured to use removed ciphers {}. '
                        'These ciphers were removed from OpenSSH and if '
                        'present the sshd daemon will not start in RHEL 8'
                        ''.format(','.join(found_ciphers)),
                remediation='Remove the following ciphers from sshd_config: '
                            '{}'.format(','.join(found_ciphers)),
                severity='high',
                flags=['inhibitor'])

        if found_macs:
            report_with_remediation(
                title='OpenSSH configured to use removed mac',
                summary='OpenSSH is configured to use removed mac {}. '
                        'This MAC was removed from OpenSSH and if present '
                        'the sshd daemon will not start in RHEL 8'
                        ''.format(','.join(found_macs)),
                remediation='Remove the following MACs from sshd_config: '
                            '{}'.format(','.join(found_macs)),
                severity='high',
                flags=['inhibitor'])
