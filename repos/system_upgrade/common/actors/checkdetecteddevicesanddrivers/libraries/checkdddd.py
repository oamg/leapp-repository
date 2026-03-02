from collections import defaultdict
from enum import IntEnum

from leapp import reporting
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
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
                'Leapp detected loaded kernel drivers which have been'
                ' removed in {target_distro} {version}. Upgrade cannot'
                ' proceed.'.format(**DISTRO_REPORT_NAMES, version=get_target_major_version())
            ),
            reporting.Summary(
                (
                    'Support for the following {source_distro} {source_version} device drivers has'
                    ' been removed in {target_distro} {target_version}:\n'
                    '     - {drivers}\n'
                ).format(
                    drivers='\n     - '.join([entry.driver_name for entry in drivers]),
                    target_version=get_target_major_version(),
                    source_version=get_source_major_version(),
                    **DISTRO_REPORT_NAMES
                )
            ),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/6971716',
                title=('Leapp preupgrade getting "Inhibitor: Detected loaded kernel drivers which have been '
                       'removed in RHEL {target}. Upgrade cannot proceed."').format(target=get_target_major_version())
            ),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/5436131',
                title=(
                    'Leapp upgrade fail with error "Inhibitor: Detected loaded kernel drivers which '
                    'have been removed in RHEL {target}. Upgrade cannot proceed."'
                ).format(
                    target=get_target_major_version()
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.DRIVERS]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Key('f08a07da902958defa4f5c2699fae9ec2eb67c5b'),
        ])

    devices = inhibiting_entries.get(MessagingClass.DEVICES)
    if devices:
        reporting.create_report([
            reporting.Title(
                'Leapp detected devices which are no longer supported in {target_distro} {version}.'
                ' Upgrade cannot proceed.'.format(**DISTRO_REPORT_NAMES, version=get_target_major_version())
            ),
            reporting.Summary(
                (
                    'Support for the following devices has been removed in {target_distro} {version}:\n'
                    '     - {devices}\n'
                ).format(
                    devices='\n     - '.join(['{name} ({pci})'.format(name=entry.device_name,
                                             pci=entry.device_id) for entry in devices]),
                    version=get_target_major_version(),
                    **DISTRO_REPORT_NAMES
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Key('ccfc28592c82123649fc824c6c1c89cabfceae7c'),
        ])

    cpus = inhibiting_entries.get(MessagingClass.CPUS)
    if cpus:
        reporting.create_report([
            reporting.Title(
                'Leapp detected a processor which is no longer supported in'
                ' {target_distro} {version}. Upgrade cannot proceed.'.format(
                    **DISTRO_REPORT_NAMES, version=get_target_major_version())
            ),
            reporting.Summary(
                (
                    'Support for the following processors has been removed in {target_distro} {version}:\n'
                    '     - {processors}\n'
                ).format(
                    processors='\n     - '.join([entry.device_name for entry in cpus]),
                    version=get_target_major_version(),
                    **DISTRO_REPORT_NAMES
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Key('e3e9e4d2566733e2f843db9823c8568b9b6922f9'),
        ])


def create_warnings(unmaintained_entries):
    if not unmaintained_entries:
        return

    drivers = unmaintained_entries.get(MessagingClass.DRIVERS)
    if drivers:
        reporting.create_report([
            reporting.Title(
                'Leapp detected loaded kernel drivers which are no longer maintained in'
                ' {target_distro} {version}.'.format(**DISTRO_REPORT_NAMES, version=get_target_major_version())
            ),
            reporting.Summary(
                (
                    'The following {source_distro} {source_version} device drivers are no longer'
                    ' maintained {target_distro} {target_version}:\n'
                    '     - {drivers}\n'
                ).format(
                    drivers='\n     - '.join([entry.driver_name for entry in drivers]),
                    target_version=get_target_major_version(),
                    source_version=get_source_major_version(),
                    **DISTRO_REPORT_NAMES
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.DRIVERS]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Key('0ff2413fd3cb0358736bf9be597f4dbdf58f2c4d'),
        ])

    devices = unmaintained_entries.get(MessagingClass.DEVICES)
    if devices:
        reporting.create_report([
            reporting.Title(
                'Leapp detected devices which are no longer maintained in'
                ' {target_distro} {version}'.format(**DISTRO_REPORT_NAMES, version=get_target_major_version())
            ),
            reporting.Summary(
                (
                    'The support for the following devices has been removed in {target_distro} {version} and '
                    'are no longer maintained:\n     - {devices}\n'
                ).format(
                    devices='\n     - '.join(['{name} ({pci})'.format(name=entry.device_name,
                                             pci=entry.device_id) for entry in devices]),
                    version=get_target_major_version(),
                    **DISTRO_REPORT_NAMES
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Key('261e3e55a3a80346f2fcc2a1e59c64f7a4caa263'),
        ])

    cpus = unmaintained_entries.get(MessagingClass.CPUS)
    if cpus:
        reporting.create_report([
            reporting.Title(
                'Leapp detected a processor which is no longer maintained in {target_distro} {version}.'.format(
                    **DISTRO_REPORT_NAMES, version=get_target_major_version())
            ),
            reporting.Summary(
                (
                    'The following processors are no longer maintained in {target_distro} {version}:\n'
                    '     - {processors}\n'
                ).format(
                    processors='\n     - '.join([entry.device_name for entry in cpus]),
                    version=get_target_major_version(),
                    **DISTRO_REPORT_NAMES
                )
            ),
            reporting.Audience('sysadmin'),
            reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Key('61eb181bbc56328fbe03b5229d25a8ea5ebdc7a2'),
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
