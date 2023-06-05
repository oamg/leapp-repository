import os

from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import IfCfg, InstalledRPM, RpmTransactionTasks

FMT_LIST_SEPARATOR = '\n    - '


def process():
    TRUE_VALUES = ['yes', 'true', '1']
    TYPE_MAP = {
        'ethernet':     'NetworkManager',
        'ctc':          'NetworkManager',
        'infiniband':   'NetworkManager',
        'bond':         'NetworkManager',
        'vlan':         'NetworkManager',
        'bridge':       'NetworkManager',
        'wireless':     'NetworkManager-wifi',
        'team':         'NetworkManager-team',
    }

    bad_type_files = []
    not_controlled_files = []
    rpms_to_install = []

    if not has_package(InstalledRPM, 'network-scripts'):
        # If network-scripts package was not installed,
        # we don't do anything.
        return

    for ifcfg in api.consume(IfCfg):
        bad_type = False
        got_type = None
        nm_controlled = True

        if ifcfg.rules is not None or ifcfg.rules6 is not None:
            if 'NetworkManager-dispatcher-routing-rules' not in rpms_to_install:
                rpms_to_install.append('NetworkManager-dispatcher-routing-rules')
            continue

        if os.path.basename(ifcfg.filename) == 'ifcfg-lo':
            continue

        for prop in ifcfg.properties:
            if prop.name in ('TYPE', 'DEVICETYPE'):
                if got_type is None:
                    got_type = prop.value.lower()
                elif got_type != prop.value.lower():
                    bad_type = True

            if prop.name == 'BONDING_MASTER':
                if got_type is None:
                    got_type = 'bond'
                elif got_type != 'bond':
                    bad_type = True

            if prop.name == 'NM_CONTROLLED' and prop.value.lower() not in TRUE_VALUES:
                nm_controlled = False

        if got_type in TYPE_MAP:
            if TYPE_MAP[got_type] not in rpms_to_install:
                rpms_to_install.append(TYPE_MAP[got_type])
        else:
            bad_type = True

        # Don't bother reporting the file for NM_CONTROLLED=no
        # if its type is not supportable with NetworkManager anyway
        if bad_type is True:
            bad_type_files.append(ifcfg.filename)
        elif nm_controlled is False:
            not_controlled_files.append(ifcfg.filename)

    if bad_type_files:
        title = 'Network configuration for unsupported device types detected'
        summary = ('RHEL 9 does not support the legacy network-scripts'
                   ' package that was deprecated in RHEL 8 in favor of'
                   ' NetworkManager. Files for device types that are not'
                   ' supported by NetworkManager are present in the system.'
                   ' Files with the problematic configuration:{}').format(
            ''.join(['{}{}'.format(FMT_LIST_SEPARATOR, bfile) for bfile in bad_type_files])
        )
        remediation = ('Consult the nm-settings-ifcfg-rh(5) manual for'
                       ' valid types of ifcfg files. Remove configuration'
                       ' files that can not be supported.')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Remediation(hint=remediation),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.RelatedResource('package', 'NetworkManager'),
        ] + [
            reporting.RelatedResource('file', fname)
            for fname in bad_type_files
        ])

    if not_controlled_files:
        title = 'Network configuration with disabled NetworkManager support detected'
        summary = ('RHEL 9 does not support the legacy network-scripts'
                   ' package that was deprecated in RHEL 8 in favor of'
                   ' NetworkManager. Configuration present in the system'
                   ' prohibit NetworkManager from loading it.'
                   ' Files with the problematic configuration:{}').format(
            ''.join(['{}{}'.format(FMT_LIST_SEPARATOR, bfile) for bfile in not_controlled_files])
        )
        remediation = ('Ensure the ifcfg files comply with format described in'
                       ' nm-settings-ifcfg-rh(5) manual and remove the'
                       ' NM_CONTROLLED key from them.')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Remediation(hint=remediation),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.RelatedResource('package', 'NetworkManager'),
            reporting.ExternalLink(
                title='nm-settings-ifcfg-rh - Description of ifcfg-rh settings plugin',
                url='https://red.ht/nm-settings-ifcfg-rh',
            ),
        ] + [
            reporting.RelatedResource('file', fname)
            for fname in not_controlled_files
        ])

    if rpms_to_install:
        if not has_package(InstalledRPM, 'NetworkManager'):
            # If the user was not using NetworkManager previously,
            # make sure NetworkManager is configured consistently with how
            # network-scripts behaved.
            rpms_to_install.append('NetworkManager-config-server')
        api.produce(RpmTransactionTasks(to_install=rpms_to_install))
