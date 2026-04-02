from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, PulseAudioConfiguration

FMT_LIST_SEPARATOR = '\n    - '


def _report_custom_pulseaudio_config(modified_defaults, dropin_dirs, user_config_dirs):
    """
    Create a report warning about custom PulseAudio configuration.

    :param modified_defaults: list of modified default config files
    :type modified_defaults: list
    :param dropin_dirs: list of drop-in directories with content
    :type dropin_dirs: list
    :param user_config_dirs: list of per-user config directories
    :type user_config_dirs: list
    """
    details = []
    if modified_defaults:
        details.append(
            'The following default PulseAudio configuration files have been modified:{sep}{files}'.format(
                sep=FMT_LIST_SEPARATOR,
                files=FMT_LIST_SEPARATOR.join(modified_defaults),
            )
        )
    if dropin_dirs:
        details.append(
            'The following PulseAudio drop-in configuration directories contain custom '
            'fragments:{sep}{dirs}'.format(
                sep=FMT_LIST_SEPARATOR,
                dirs=FMT_LIST_SEPARATOR.join(dropin_dirs),
            )
        )
    if user_config_dirs:
        details.append(
            'Per-user PulseAudio configuration was found in:{sep}{dirs}'.format(
                sep=FMT_LIST_SEPARATOR,
                dirs=FMT_LIST_SEPARATOR.join(user_config_dirs),
            )
        )

    summary = (
        'PulseAudio is replaced by PipeWire in {target_distro} 10. The PipeWire pipewire-pulseaudio plugin provides '
        'compatibility with the default PulseAudio configuration, but custom PulseAudio configuration will '
        'not be applied after the upgrade. Review your PulseAudio configuration and migrate any custom '
        'settings to PipeWire equivalents after upgrading.'
    ).format_map(DISTRO_REPORT_NAMES)
    if details:
        summary += '\n\n' + '\n\n'.join(details)

    all_paths = modified_defaults + dropin_dirs + user_config_dirs
    reporting.create_report([
        reporting.Title('Custom PulseAudio configuration detected'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrate PulseAudio to PipeWire',
                               url='https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/Migrate-PulseAudio'),
        reporting.Remediation(
            hint='Review your PulseAudio configuration and plan to migrate custom settings to PipeWire '
                 'after the upgrade. The pipewire-pulseaudio plugin handles default configuration automatically.'
        ),
        reporting.RelatedResource('package', 'pulseaudio'),
    ] + [reporting.RelatedResource('file', f) for f in all_paths])


def check_pulseaudio():
    """
    Consume PulseAudioConfiguration and generate report if custom config is found.
    """
    if not has_package(DistributionSignedRPM, 'pulseaudio'):
        api.current_logger().debug('PulseAudio is not installed, skipping check.')
        return

    msg = next(api.consume(PulseAudioConfiguration), None)
    if not msg:
        api.current_logger().debug('No PulseAudioConfiguration message received.')
        return

    if msg.modified_defaults or msg.dropin_dirs or msg.user_config_dirs:
        _report_custom_pulseaudio_config(msg.modified_defaults, msg.dropin_dirs, msg.user_config_dirs)
    else:
        api.current_logger().info('No custom PulseAudio configuration detected.')
