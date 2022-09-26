from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import IfCfg, NetworkManagerConnection

FMT_LIST_SEPARATOR = '\n    - '


def process():
    wep_files = []

    # Scan NetworkManager native keyfile connections
    for nmconn in api.consume(NetworkManagerConnection):
        for setting in nmconn.settings:
            if not setting.name == 'wifi-security':
                continue

            for prop in setting.properties:
                if not prop.name == 'key-mgmt':
                    continue
                if prop.value in ('none', 'ieee8021x'):
                    wep_files.append(nmconn.filename)

    # Scan legacy ifcfg files & secrets
    for ifcfg in api.consume(IfCfg):
        props = ifcfg.properties
        if ifcfg.secrets is not None:
            props = props + ifcfg.secrets

        for prop in props:
            name = prop.name
            value = prop.value

            # Dynamic WEP
            if name == 'KEY_MGMT' and value.upper() == 'IEEE8021X':
                wep_files.append(ifcfg.filename)
                continue

            # Static WEP, possibly with agent-owned secrets
            if name in ('KEY_PASSPHRASE1', 'KEY1', 'WEP_KEY_FLAGS'):
                wep_files.append(ifcfg.filename)
                continue

    if wep_files:
        title = 'Wireless networks using unsupported WEP encryption detected'
        summary = ('The Wired Equivalent Privacy (WEP) algorithm used for'
                   ' authenticating to wireless networks has been phased out'
                   ' due to known security weaknesses. Configuration for networks'
                   ' that use the phased out WEP algorithm is present in the system'
                   ' and will not work after the upgrade.'
                   ' Files with the problematic configuration:{}').format(
            ''.join(['{}{}'.format(FMT_LIST_SEPARATOR, bfile) for bfile in wep_files])
        )
        remediation = ('Remove configuration for networks that use WEP or'
                       ' upgrade the networks to use more secure encryption'
                       ' algorithms, such as ones defined by WPA2 or WPA3.')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Remediation(hint=remediation),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.RelatedResource('package', 'NetworkManager-wifi'),
        ] + [
            reporting.RelatedResource('file', fname)
            for fname in wep_files
        ])
