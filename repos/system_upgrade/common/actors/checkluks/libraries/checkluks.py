from leapp import reporting
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api
from leapp.models import (
    CephInfo,
    CopyFile,
    DracutModule,
    KernelCmdline,
    LuksDumps,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import create_report

# https://red.ht/clevis-tpm2-luks-auto-unlock-rhel8
# https://red.ht/clevis-tpm2-luks-auto-unlock-rhel9
# https://red.ht/convert-to-luks2-rhel8
# https://red.ht/convert-to-luks2-rhel9
CLEVIS_DOC_URL_FMT = 'https://red.ht/clevis-tpm2-luks-auto-unlock-rhel{}'
LUKS2_CONVERT_DOC_URL_FMT = 'https://red.ht/convert-to-luks2-rhel{}'

FMT_LIST_SEPARATOR = '\n    - '


def _formatted_list_output(input_list, sep=FMT_LIST_SEPARATOR):
    return ['{}{}'.format(sep, item) for item in input_list]


def _at_least_one_tpm_token(luks_dump):
    return any(token.token_type == "clevis-tpm2" for token in luks_dump.tokens)


def _get_ceph_volumes():
    ceph_info = next(api.consume(CephInfo), None)
    return ceph_info.encrypted_volumes[:] if ceph_info else []


def report_inhibitor(luks1_partitions, no_tpm2_partitions):
    source_major_version = get_source_major_version()
    clevis_doc_url = CLEVIS_DOC_URL_FMT.format(source_major_version)
    luks2_convert_doc_url = LUKS2_CONVERT_DOC_URL_FMT.format(source_major_version)
    summary = (
        'We have detected LUKS encrypted volumes that do not meet current'
        ' criteria to be able to proceed the in-place upgrade process.'
        ' Right now the upgrade process requires for encrypted storage to be'
        ' in LUKS2 format configured with Clevis TPM 2.0.'
    )

    report_hints = []

    if luks1_partitions:

        summary += (
            '\n\nSince {target_distro} 8 the default format for LUKS encryption is LUKS2.'
            ' Despite the old LUKS1 format is still supported on {target_distro} systems'
            ' it has some limitations in comparison to LUKS2.'
            ' Only the LUKS2 format is supported for upgrades.'
            ' The following LUKS1 partitions have been discovered on your system:{partitions}'
            .format(**DISTRO_REPORT_NAMES, partitions=''.join(_formatted_list_output(luks1_partitions)))
        )
        report_hints.append(reporting.Remediation(
            hint=(
                'Convert your LUKS1 encrypted devices to LUKS2 and bind it to TPM2 using clevis.'
                ' If this is not possible in your case consider clean installation'
                ' of the target {target_distro} system instead.'.format_map(DISTRO_REPORT_NAMES)
            )
        ))
        report_hints.append(reporting.ExternalLink(
            url=luks2_convert_doc_url,
            title='LUKS versions in RHEL: Conversion'
        ))

    if no_tpm2_partitions:
        summary += (
            '\n\nCurrently we require the process to be non-interactive and'
            ' offline. For this reason we require automatic unlock of'
            ' encrypted devices during the upgrade process.'
            ' Currently we support automatic unlocking during the upgrade only'
            ' for volumes bound to Clevis TPM2 token.'
            ' The following LUKS2 devices without Clevis TPM2 token '
            ' have been discovered on your system: {}'
            .format(''.join(_formatted_list_output(no_tpm2_partitions)))
        )

        report_hints.append(reporting.Remediation(
            hint=(
                'Add Clevis TPM2 binding to LUKS devices.'
                ' If some LUKS devices use still the old LUKS1 format, convert'
                ' them to LUKS2 prior to binding.'
            )
        ))
        report_hints.append(reporting.ExternalLink(
                url=clevis_doc_url,
                title='Configuring manual enrollment of LUKS-encrypted volumes by using a TPM 2.0 policy'
            )
        )
    create_report([
        reporting.Title('Detected LUKS devices unsuitable for in-place upgrade.'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.BOOT, reporting.Groups.ENCRYPTION]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ] + report_hints)


def _emit_rdluks_undesired_for_upgrade_cmdline():
    """
    Identify rd.luks.uuid args on the source kernel cmdline and request their
    removal from the upgrade boot entry.

    The upgrade initramfs uses clevis-tpm2 to unlock LUKS devices. Dracut's
    rd.luks.uuid mechanism is not needed and can cause problems if left in.
    limits what devices will be unlocked during boot, i.e., only devices named
    in the rd.luks.uuid args will be unlocked.  However, we want to unlock all
    LUKS devices (at least those in /etc/crypttab). Therefore, we request that
    rd.luks.uuid args be removed from the upgrade kernel cmdline.
    """
    cmdline = next(api.consume(KernelCmdline), None)
    if not cmdline:
        api.current_logger().debug('No KernelCmdline message received, nothing to do.')
        return

    rdluks_args = [arg for arg in cmdline.parameters if arg.key == 'rd.luks.uuid']

    if not rdluks_args:
        api.current_logger().debug('No rd.luks.uuid args found on the source kernel cmdline.')
        return

    api.current_logger().debug(
        'Requesting removal of rd.luks.uuid args from the upgrade kernel cmdline: %s',
        ['{}={}'.format(a.key, a.value) for a in rdluks_args]
    )
    api.produce(UpgradeKernelCmdlineArgTasks(to_remove=rdluks_args))

    # When installing the target kernel RPM, the cmdline is copied from the booted system.
    # As we remove the rd.luks.uuid args, we would accidentally remove them also from the
    # target entry. Therefore, we add them back in here.
    api.produce(TargetKernelCmdlineArgTasks(to_add=rdluks_args))


def check_invalid_luks_devices():
    luks_dumps = next(api.consume(LuksDumps), None)
    if not luks_dumps:
        api.current_logger().debug('No LUKS volumes detected. Skipping.')
        return

    luks1_partitions = []
    no_tpm2_partitions = []
    ceph_vol = _get_ceph_volumes()
    for luks_dump in luks_dumps.dumps:
        # if the device is managed by ceph, don't inhibit
        if luks_dump.device_name in ceph_vol:
            api.current_logger().debug('Skipping LUKS CEPH volume: {}'.format(luks_dump.device_name))
            continue

        if luks_dump.version == 1:
            luks1_partitions.append(luks_dump.device_name)
        elif luks_dump.version == 2 and not _at_least_one_tpm_token(luks_dump):
            no_tpm2_partitions.append(luks_dump.device_name)

        if luks1_partitions or no_tpm2_partitions:
            report_inhibitor(luks1_partitions, no_tpm2_partitions)
        else:
            required_crypt_rpms = [
                'clevis',
                'clevis-dracut',
                'clevis-systemd',
                'clevis-udisks2',
                'clevis-luks',
                'cryptsetup',
                'tpm2-tss',
                'tpm2-tools',
                'tpm2-abrmd'
            ]
            api.produce(TargetUserSpaceUpgradeTasks(
                copy_files=[CopyFile(src="/etc/crypttab")],
                install_rpms=required_crypt_rpms)
            )
            api.produce(UpgradeInitramfsTasks(
                include_files=['/etc/crypttab'],
                include_dracut_modules=[
                    DracutModule(name='clevis'),
                    DracutModule(name='clevis-pin-tpm2')
                ])
            )
            _emit_rdluks_undesired_for_upgrade_cmdline()
