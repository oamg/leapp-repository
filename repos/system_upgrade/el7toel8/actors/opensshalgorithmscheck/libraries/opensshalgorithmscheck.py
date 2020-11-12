from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp import reporting


def process(openssh_messages):
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

    config = next(openssh_messages, None)
    if list(openssh_messages):
        api.current_logger().warning('Unexpectedly received more than one OpenSshConfig message.')
    if not config:
        raise StopActorExecutionError(
            'Could not check openssh configuration', details={'details': 'No OpenSshConfig facts found.'}
        )

    for cipher in removed_ciphers:
        if config.ciphers and cipher in config.ciphers:
            found_ciphers.append(cipher)
    for mac in removed_macs:
        if config.macs and mac in config.macs:
            found_macs.append(mac)

    resources = [
        reporting.RelatedResource('package', 'openssh-server'),
        reporting.RelatedResource('file', '/etc/ssh/sshd_config')
    ]
    if found_ciphers:
        reporting.create_report([
            reporting.Title('OpenSSH configured to use removed ciphers'),
            reporting.Summary(
                'OpenSSH is configured to use removed ciphers {}. '
                'These ciphers were removed from OpenSSH and if '
                'present the sshd daemon will not start in RHEL 8'
                ''.format(','.join(found_ciphers))
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES,
                    reporting.Groups.INHIBITOR
            ]),
            reporting.Remediation(
                hint='Remove the following ciphers from sshd_config: '
                     '{}'.format(','.join(found_ciphers))
            ),
        ] + resources)

    if found_macs:
        reporting.create_report([
            reporting.Title('OpenSSH configured to use removed mac'),
            reporting.Summary(
                'OpenSSH is configured to use removed mac {}. '
                'This MAC was removed from OpenSSH and if present '
                'the sshd daemon will not start in RHEL 8'
                ''.format(','.join(found_macs))
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES,
                    reporting.Groups.INHIBITOR
            ]),
            reporting.Remediation(
                hint='Remove the following MACs from sshd_config: {}'.format(','.join(found_macs))
            ),
        ] + resources)
