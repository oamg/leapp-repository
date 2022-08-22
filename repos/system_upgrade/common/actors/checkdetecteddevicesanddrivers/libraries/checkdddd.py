from collections import defaultdict
from enum import IntEnum

from leapp import reporting
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import DetectedDeviceOrDriver


class MessagingClass(IntEnum):
    UNKNOWN = 0
    DRIVERS = 1
    DEVICES = 2
    CPUS = 3


def create_inhibitors(inhibiting_entries):
    if not inhibiting_entries:
        return

    drivers = inhibiting_entries.get(MessagingClass.DRIVERS)
    if drivers:
        reporting.create_report([
            reporting.Title(
                'Leapp detected loaded kernel drivers which have been removed '
                'in RHEL {}. Upgrade cannot proceed.'.format(get_target_major_version())
            ),
            reporting.Summary(
                (
                    'Support for the following RHEL {source} device drivers has been removed in RHEL {target}:\n'
                    '     - {drivers}\n'
                ).format(
                    drivers='\n     - '.join([entry.driver_name for entry in drivers]),
                    target=get_target_major_version(),
                    source=get_source_major_version(),
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.DRIVERS]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR])
        ])

    devices = inhibiting_entries.get(MessagingClass.DEVICES)
    if devices:
        reporting.create_report([
            reporting.Title(
                'Leapp detected devices which are no longer supported in RHEL {}. Upgrade cannot proceed.'.format(
                    get_target_major_version())
            ),
            reporting.Summary(
                (
                    'Support for the following devices has been removed in RHEL {target}:\n'
                    '     - {devices}\n'
                ).format(
                    devices='\n     - '.join(['{name} ({pci})'.format(name=entry.device_name,
                                             pci=entry.device_id) for entry in devices]),
                    target=get_target_major_version(),
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR])
        ])

    cpus = inhibiting_entries.get(MessagingClass.CPUS)
    if cpus:
        reporting.create_report([
            reporting.Title(
                'Leapp detected a processor which is no longer supported in RHEL {}. Upgrade cannot proceed.'.format(
                    get_target_major_version())
            ),
            reporting.Summary(
                (
                    'Support for the following processors has been removed in RHEL {target}:\n'
                    '     - {processors}\n'
                ).format(
                    processors='\n     - '.join([entry.device_name for entry in cpus]),
                    target=get_target_major_version(),
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR])
        ])


def create_warnings(unmaintained_entries):
    if not unmaintained_entries:
        return

    drivers = unmaintained_entries.get(MessagingClass.DRIVERS)
    if drivers:
        reporting.create_report([
            reporting.Title(
                'Leapp detected loaded kernel drivers which are no longer maintained in RHEL {}.'.format(
                    get_target_major_version())
            ),
            reporting.Summary(
                (
                    'The following RHEL {source} device drivers are no longer maintained RHEL {target}:\n'
                    '     - {drivers}\n'
                ).format(
                    drivers='\n     - '.join([entry.driver_name for entry in drivers]),
                    target=get_target_major_version(),
                    source=get_source_major_version(),
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.DRIVERS]),
            reporting.Severity(reporting.Severity.HIGH),
        ])

    devices = unmaintained_entries.get(MessagingClass.DEVICES)
    if devices:
        reporting.create_report([
            reporting.Title(
                'Leapp detected devices which are no longer maintained in RHEL {}'.format(
                    get_target_major_version())
            ),
            reporting.Summary(
                (
                    'The support for the following devices has been removed in RHEL {target} and '
                    'are no longer maintained:\n     - {devices}\n'
                ).format(
                    devices='\n     - '.join(['{name} ({pci})'.format(name=entry.device_name,
                                             pci=entry.device_id) for entry in devices]),
                    target=get_target_major_version(),
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL]),
            reporting.Severity(reporting.Severity.HIGH),
        ])

    cpus = unmaintained_entries.get(MessagingClass.CPUS)
    if cpus:
        reporting.create_report([
            reporting.Title(
                'Leapp detected a processor which is no longer maintained in RHEL {}.'.format(
                    get_target_major_version())
            ),
            reporting.Summary(
                (
                    'The following processors are no longer maintained in RHEL {target}:\n'
                    '     - {processors}\n'
                ).format(
                    processors='\n     - '.join([entry.device_name for entry in cpus]),
                    target=get_target_major_version(),
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.HIGH),
        ])


def classify(entry):
    if entry.device_type == 'pci':
        if entry.device_id:
            return MessagingClass.DEVICES
        return MessagingClass.DRIVERS
    if entry.device_type == 'cpu':
        return MessagingClass.CPUS
    return MessagingClass.UNKNOWN


def process():
    target_version = int(get_target_major_version())
    inhibiting = defaultdict(list)
    unmaintained = defaultdict(list)
    for entry in api.consume(DetectedDeviceOrDriver):
        if target_version not in entry.available_in_rhel:
            inhibiting[classify(entry)].append(entry)
        elif target_version not in entry.maintained_in_rhel:
            unmaintained[classify(entry)].append(entry)
    create_inhibitors(inhibiting)
    create_warnings(unmaintained)
