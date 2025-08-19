from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import DnfPluginPathDetected

DNF_CONFIG_PATH = '/etc/dnf/dnf.conf'


def check_dnf_pluginpath(dnf_pluginpath_detected):
    """Create an inhibitor when pluginpath is detected in DNF configuration."""
    if not dnf_pluginpath_detected.is_pluginpath_detected:
        return
    reporting.create_report([
        reporting.Title('Detected specified pluginpath in DNF configuration.'),
        reporting.Summary(
            'The "pluginpath" option is set in the {} file. The path to DNF plugins differs between '
            'system major releases due to different versions of Python. '
            'This breaks the in-place upgrades if defined explicitly as DNF plugins '
            'are stored on a different path on the new system.'
            .format(DNF_CONFIG_PATH)
        ),
        reporting.Remediation(
            hint='Remove or comment out the pluginpath option in the DNF '
                 'configuration file to be able to upgrade the system',
            commands=[['sed', '-i', '\'s/^pluginpath[[:space:]]*=/#pluginpath=/\'', DNF_CONFIG_PATH]],
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('file', DNF_CONFIG_PATH),
    ])


def perform_check():
    dnf_pluginpath_detected = next(api.consume(DnfPluginPathDetected), None)
    if dnf_pluginpath_detected:
        check_dnf_pluginpath(dnf_pluginpath_detected)
