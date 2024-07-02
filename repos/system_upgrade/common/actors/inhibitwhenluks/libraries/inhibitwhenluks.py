from leapp import reporting
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import CephInfo, DracutModule, LuksDumps, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks
from leapp.reporting import create_report

CLEVIS_RHEL8_DOC_URL = 'https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/security_hardening/configuring-automated-unlocking-of-encrypted-volumes-using-policy-based-decryption_security-hardening#configuring-manual-enrollment-of-volumes-using-tpm2_configuring-automated-unlocking-of-encrypted-volumes-using-policy-based-decryption'  # noqa: E501; pylint: disable=line-too-long
CLEVIS_RHEL9_DOC_URL = 'https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/security_hardening/configuring-automated-unlocking-of-encrypted-volumes-using-policy-based-decryption_security-hardening#configuring-manual-enrollment-of-volumes-using-tpm2_configuring-automated-unlocking-of-encrypted-volumes-using-policy-based-decryption'  # noqa: E501; pylint: disable=line-too-long
LUKS2_CONVERT_RHEL8_DOC_URL = 'https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/security_hardening/encrypting-block-devices-using-luks_security-hardening#luks-versions-in-rhel_encrypting-block-devices-using-luks'  # noqa: E501; pylint: disable=line-too-long
LUKS2_CONVERT_RHEL9_DOC_URL = 'https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/security_hardening/encrypting-block-devices-using-luks_security-hardening#luks-versions-in-rhel_encrypting-block-devices-using-luks'  # noqa: E501; pylint: disable=line-too-long
FMT_LIST_SEPARATOR = '\n    - '


def _at_least_one_tpm_token(luks_dump):
    return any([token.token_type == "clevis-tpm2" for token in luks_dump.tokens])


def check_invalid_luks_devices():
    target_major_version = get_target_major_version()
    if target_major_version == '8':
        clevis_doc_url = CLEVIS_RHEL8_DOC_URL
        luks2_convert_doc_url = LUKS2_CONVERT_RHEL8_DOC_URL
    elif target_major_version == '9':
        clevis_doc_url = CLEVIS_RHEL9_DOC_URL
        luks2_convert_doc_url = LUKS2_CONVERT_RHEL9_DOC_URL
    else:
        create_report([
            reporting.Title('LUKS encrypted partition detected'),
            reporting.Summary('Upgrading system with encrypted partitions is not supported'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.BOOT, reporting.Groups.ENCRYPTION]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
        ])
        return
    ceph_vol = []
    try:
        ceph_info = next(api.consume(CephInfo), None)
        if ceph_info:
            ceph_vol = ceph_info.encrypted_volumes[:]
    except StopIteration:
        pass

    luks_dumps = next(api.consume(LuksDumps), None)
    if luks_dumps is None:
        return

    for luks_dump in luks_dumps.dumps:
        # if the device is managed by ceph, don't inhibit
        if luks_dump.device_name in ceph_vol:
            continue

        list_luks1_partitions = []
        list_no_tpm2_partitions = []

        if luks_dump.version == 1:
            list_luks1_partitions.append(luks_dump.device_name)
        elif luks_dump.version == 2 and not _at_least_one_tpm_token(luks_dump):
            list_no_tpm2_partitions.append(luks_dump.device_name)

        if list_luks1_partitions or list_no_tpm2_partitions:
            summary = (
                    'Only systems where all encrypted devices are LUKS2 '
                    'devices with Clevis TPM 2.0 token can be updated.'
            )
            report_hints = []

            if list_luks1_partitions:
                luks1_partitions_text = ''
                for partition in list_luks1_partitions:
                    luks1_partitions_text += '{0}{1}'.format(FMT_LIST_SEPARATOR, partition)

                summary += '\nThe following LUKS1 partitions have been discovered on your system: '
                summary += luks1_partitions_text
                report_hints.append(reporting.Remediation(
                    hint=("Convert your LUKS1 encrypted partition to LUKS2 and bind it to TPM2 using clevis.")
                ))
                report_hints.append(reporting.ExternalLink(
                    url=luks2_convert_doc_url,
                    title='LUKS versions in RHEL: Conversion'
                ))

            if list_no_tpm2_partitions:
                no_tpm2_partitions_text = ''
                for partition in list_no_tpm2_partitions:
                    no_tpm2_partitions_text += '{0}{1}'.format(FMT_LIST_SEPARATOR, partition)

                summary += ('\nThe following LUKS2 devices without clevis TPM2 token '
                            'have been discovered on your system:')
                summary += no_tpm2_partitions_text

                report_hints.append(reporting.Remediation(hint="Add Clevis TPM2 binding to the volume."))
                report_hints.append(reporting.ExternalLink(
                        url=clevis_doc_url,
                        title='Configuring manual enrollment of LUKS-encrypted volumes by using a TPM 2.0 policy'
                    )
                )

            create_report([
                reporting.Title('Invalid LUKS encrypted partition detected'),
                reporting.Summary(summary),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.BOOT, reporting.Groups.ENCRYPTION]),
                reporting.Groups([reporting.Groups.INHIBITOR]),
            ] + report_hints)
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
            api.produce(TargetUserSpaceUpgradeTasks(install_rpms=required_crypt_rpms))
            api.produce(UpgradeInitramfsTasks(include_dracut_modules=[
                DracutModule(name='clevis'), DracutModule(name='clevis-pin-tpm2')]))
