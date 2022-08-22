import errno
import os

from leapp import reporting
from leapp.libraries.common import utils

SYSCONFIG_DIR = '/etc/sysconfig/network-scripts'
NM_CONN_DIR = '/etc/NetworkManager/system-connections'

FMT_LIST_SEPARATOR = '\n    - '


def process():
    wep_files = []

    # Scan NetworkManager native keyfiles
    try:
        keyfiles = os.listdir(NM_CONN_DIR)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        keyfiles = []

    for f in keyfiles:
        path = os.path.join(NM_CONN_DIR, f)

        cp = utils.parse_config(open(path, mode='r').read())

        if not cp.has_section('wifi-security'):
            continue

        key_mgmt = cp.get('wifi-security', 'key-mgmt')
        if key_mgmt in ('none', 'ieee8021x'):
            wep_files.append(path)

    # Scan legacy ifcfg files & secrets
    try:
        ifcfgs = os.listdir(SYSCONFIG_DIR)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        ifcfgs = []

    for f in ifcfgs:
        path = os.path.join(SYSCONFIG_DIR, f)

        if not f.startswith('ifcfg-') and not f.startswith('keys-'):
            continue

        for line in open(path).readlines():
            try:
                (key, value) = line.split('#')[0].strip().split('=')
            except ValueError:
                # We're not interested in lines that are not
                # simple assignments. Play it safe.
                continue

            # Dynamic WEP
            if key == 'KEY_MGMT' and value.upper() == 'IEEE8021X':
                wep_files.append(path)
                continue

            # Static WEP, possibly with agent-owned secrets
            if key in ('KEY_PASSPHRASE1', 'KEY1', 'WEP_KEY_FLAGS'):
                wep_files.append(path)
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
