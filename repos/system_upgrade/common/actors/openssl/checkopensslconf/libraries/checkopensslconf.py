from leapp import reporting
from leapp.libraries.common.config import architecture, version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, TrackedFilesInfoSource

DEFAULT_OPENSSL_CONF = '/etc/pki/tls/openssl.cnf'
URL_CRYPTOPOLICIES = {
    '8': 'https://red.ht/rhel-8-system-wide-crypto-policies',
    '9': 'https://red.ht/rhel-9-system-wide-crypto-policies',
    '10': 'https://red.ht/rhel-10-system-wide-crypto-policies',  # TODO actually make the url
}


def check_ibmca():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        # not needed check really, but keeping it to make it clear
        return
    if not has_package(DistributionSignedRPM, 'openssl-ibmca'):
        return
    # In RHEL 9 has been introduced new technology: openssl providers. The engine
    # is deprecated, so keep proper teminology to not confuse users.
    summary = (
        'The presence of openssl-ibmca package suggests that the system may be configured'
        ' to use the IBMCA OpenSSL engine.'
        ' Due to major changes in OpenSSL and libica between RHEL {source} and RHEL {target} it is not'
        ' possible to migrate OpenSSL configuration files automatically. Therefore,'
        ' it is necessary to enable IBMCA providers in the OpenSSL config file manually'
        ' after the system upgrade.'
        .format(
            source=version.get_source_major_version(),
            target=version.get_target_major_version(),
        )
    )

    hint = (
        'Configure the IBMCA providers manually after the upgrade.'
        ' Please, be aware that it is not recommended to configure the system default'
        ' {fpath}. Instead, it is recommended to configure a copy of'
        ' that file and use this copy only for particular applications that are supposed'
        ' to utilize the IBMCA providers. The location of the OpenSSL configuration file'
        ' can be specified using the OPENSSL_CONF environment variable.'
        .format(fpath=DEFAULT_OPENSSL_CONF)
    )

    reporting.create_report([
        reporting.Title('Detected possible use of IBMCA in OpenSSL'),
        reporting.Summary(summary),
        reporting.Remediation(hint=hint),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([
            reporting.Groups.POST,
            reporting.Groups.ENCRYPTION
        ]),
    ])


def _is_openssl_modified():
    tracked_files = next(api.consume(TrackedFilesInfoSource), None)
    if not tracked_files:
        # unexpected at all, skipping testing, but keeping the log just in case
        api.current_logger.warning('The TrackedFilesInfoSource message is missing! Skipping check of openssl config.')
        return False
    for finfo in tracked_files.files:
        if finfo.path == DEFAULT_OPENSSL_CONF:
            return finfo.is_modified
    return False


def check_default_openssl():
    if not _is_openssl_modified():
        return

    crypto_url = URL_CRYPTOPOLICIES[version.get_target_major_version()]

    # TODO(pstodulk): Needs in future some rewording, as OpenSSL engines are
    # deprecated since "RHEL 8" and people should use OpenSSL providers instead.
    # (IIRC, they are required to use OpenSSL providers since RHEL 9.) The
    # current wording could be inaccurate.
    summary = (
        'The OpenSSL configuration file ({fpath}) has been'
        ' modified on the system. RHEL 8 (and newer) systems provide a crypto-policies'
        ' mechanism ensuring usage of system-wide secure cryptography algorithms.'
        ' Also the target system uses newer version of OpenSSL that is not fully'
        ' compatible with the current one.'
        ' To ensure the upgraded system uses crypto-policies as expected,'
        ' the new version of the openssl configuration file must be installed'
        ' during the upgrade. This will be done automatically.'
        ' The original configuration file will be saved'
        ' as "{fpath}.leappsave".'
        '\n\nNote this can affect the ability to connect to the system after'
        ' the upgrade if it depends on the current OpenSSL configuration.'
        ' Such a problem may be caused by using a particular OpenSSL engine, as'
        ' OpenSSL engines built for the'
        ' RHEL {source} system are not compatible with RHEL {target}.'
        .format(
            fpath=DEFAULT_OPENSSL_CONF,
            source=version.get_source_major_version(),
            target=version.get_target_major_version()
        )
    )
    if version.get_target_major_version() == '9':
        # NOTE(pstodulk): that a try to make things with engine/providers a
        # little bit better (see my TODO note above)
        summary += (
            '\n\nNote the legacy ENGINE API is deprecated since RHEL 8 and'
            ' it is required to use the new OpenSSL providers API instead on'
            ' RHEL 9 systems.'
        )
    hint = (
        'Check that your ability to login to the system does not depend on'
        ' the OpenSSL configuration. After the upgrade, review the system configuration'
        ' and configure the system as needed.'
        ' Please, be aware that it is not recommended to configure the system default'
        ' {fpath}. Instead, it is recommended to copy the file and use this copy'
        ' to configure particular applications.'
        ' The default OpenSSL configuration file should be modified only'
        ' when it is really necessary.'
    )
    reporting.create_report([
        reporting.Title('The /etc/pki/tls/openssl.cnf file is modified and will be replaced during the upgrade.'),
        reporting.Summary(summary),
        reporting.Remediation(hint=hint),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.POST, reporting.Groups.SECURITY]),
        reporting.RelatedResource('file', DEFAULT_OPENSSL_CONF),
        reporting.ExternalLink(
            title='Using system-wide cryptographic policies.',
            url=crypto_url
        )
    ])


def process():
    check_ibmca()
    check_default_openssl()
