from leapp import reporting
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import DefaultGrubInfo

_DEFAULT_GRUB_PATH = '/etc/default/grub'
_OPTION_NAME = 'GRUB_DEFAULT'
_EXPECTED_VALUE = 'saved'


def _get_grub_default(default_grub_msg):
    """
    Get the value of GRUB_DEFAULT from the /etc/default/grub file.

    :returns: The value without quotes, or None when the option is not set.
    """
    value = None
    for option in default_grub_msg.default_grub_info:
        if option.name == _OPTION_NAME:
            # the last definition wins as the file is sourced by shell
            value = option.value.strip().strip('"\'')
    return value


def _report_saved_entry_not_used(grub_default):
    if grub_default:
        current_setting = 'is set to "{}"'.format(grub_default)
    else:
        current_setting = 'is not set, which is the same as setting it to "0"'

    summary = (
        'The {option} option in {path} {setting}. GRUB uses the default boot entry saved in'
        ' the GRUB environment block (e.g. the one set by grubby) only when {option} is set to "{expected}".'
        ' With the current configuration the saved default boot entry is ignored and GRUB always'
        ' boots the boot entry {option} refers to.\n\n'
        'Leapp makes sure the system is booted into the upgrade environment after the reboot regardless'
        ' of this setting. However, the default boot entry Leapp sets for the kernel of the target system'
        ' is ignored as well, so the upgraded system might be booted with an unexpected boot entry.'
    ).format(option=_OPTION_NAME, path=_DEFAULT_GRUB_PATH, setting=current_setting, expected=_EXPECTED_VALUE)

    hint = (
        'If the current setting is not intentional, set {option}={expected} in {path} and regenerate the GRUB'
        ' configuration file using grub2-mkconfig. Otherwise verify after the upgrade that the system'
        ' boots the expected kernel.'
    ).format(option=_OPTION_NAME, path=_DEFAULT_GRUB_PATH, expected=_EXPECTED_VALUE)

    reporting.create_report([
        reporting.Title('GRUB is not configured to boot the saved default boot entry'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.BOOT]),
        reporting.Remediation(hint=hint),
        reporting.RelatedResource('file', _DEFAULT_GRUB_PATH),
    ])


def process():
    if architecture.matches_architecture(architecture.ARCH_S390X):
        # ZIPL is used instead of GRUB on s390x
        return

    default_grub_msg = next(api.consume(DefaultGrubInfo), None)
    if not default_grub_msg or not default_grub_msg.default_grub_info:
        # A missing or empty /etc/default/grub file is handled by other actors.
        api.current_logger().debug('No content of {} received, skipping the check.'.format(_DEFAULT_GRUB_PATH))
        return

    grub_default = _get_grub_default(default_grub_msg)
    if grub_default == _EXPECTED_VALUE:
        return

    _report_saved_entry_not_used(grub_default)
