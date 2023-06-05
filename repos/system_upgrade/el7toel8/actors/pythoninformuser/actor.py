from leapp import reporting
from leapp.actors import Actor
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class PythonInformUser(Actor):
    name = "python_inform_user"
    description = "This actor informs the user of differences in Python version and support in RHEL 8."
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        url = "https://red.ht/rhel-8-python"
        title = "Difference in Python versions and support in RHEL 8"
        summary = ("In RHEL 8, there is no 'python' command."
                   " Python 3 (backward incompatible) is the primary Python version"
                   " and Python 2 is available with limited support and limited set of packages."
                   " If you no longer require Python 2 packages following the upgrade, please remove them."
                   " Read more here: {}".format(url))
        create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.PYTHON]),
            reporting.Audience('developer'),
            reporting.ExternalLink(url, title),
            reporting.Remediation(hint='Please run "alternatives --set python /usr/bin/python3" after upgrade'),
            reporting.RelatedResource('package', 'python'),
            reporting.RelatedResource('package', 'python2'),
            reporting.RelatedResource('package', 'python3')
        ])
