from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import DnfPluginPathDetected

DNF_CONFIG_PATH = '/etc/dnf/dnf.conf'


def check_dnf_pluginpath(dnf_pluginpath_detected):
    """Create an inhibitor when pluginpath is detected in DNF configuration."""
    if dnf_pluginpath_detected.is_pluginpath_detected:
        reporting.create_report([
            reporting.Title('Detected specified pluginpath in DNF configuration.'),
            reporting.Summary(
                'The option "pluginpath" is set in {}. The path of plugins are evolving between '
                'system releases which can cause issues with the upgrade. '
                .format(DNF_CONFIG_PATH)
            ),
            reporting.Remediation(
                hint='Option pluginpath needs to be removed or commented out before running the upgrade. '
                     'Use "sed -i "s/^pluginpath=.*/#pluginpath=/" /etc/dnf/dnf.conf" '
                     'to comment out the option and remove the value.'
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.RelatedResource('file', DNF_CONFIG_PATH),
        ])


def perform_check():
    dnf_pluginpath_detected = next(api.consume(DnfPluginPathDetected))
    check_dnf_pluginpath(dnf_pluginpath_detected)
