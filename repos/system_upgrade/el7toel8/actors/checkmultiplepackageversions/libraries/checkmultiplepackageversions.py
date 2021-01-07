from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRPM
from leapp.reporting import create_report, Title, Summary, Severity, Flags, Remediation, RelatedResource

# package_name: remedy information
PROBLEM_PACKAGE_MAP = {
    'brlapi.i686': {'bugzilla': None},
    'gnome-online-accounts-devel.i686': {
        'bugzilla': 'https://bugzilla.redhat.com/show_bug.cgi?id=1765627'},
    'geocode-glib-devel.i686': {
        'bugzilla': 'https://bugzilla.redhat.com/show_bug.cgi?id=1765629'}}


def check():
    actual_problems = []
    related_resources = []
    for package, details in PROBLEM_PACKAGE_MAP.items():
        name, arch = package.split('.')
        if has_package(InstalledRPM, name, arch) and has_package(InstalledRPM, name, 'x86_64'):
            actual_problems.append(package)
        # generate RelatedResources for the report
        related_resources.append(RelatedResource('package', package))
        if details['bugzilla']:
            related_resources.append(RelatedResource('bugzilla', details['bugzilla']))

    if actual_problems:
        remediation = ["yum", "remove", "-y"] + actual_problems
        # create a single report entry for all problematic packages
        create_report([
            Title('Some packages have both 32bit and 64bit version installed which are known '
                  'to cause rpm transaction test to fail'),
            Summary('The following packages have both 32bit and 64bit version installed which are known '
                    'to cause rpm transaction test to fail:\n{}'.format(
                        '\n'.join(['- {}'.format(a) for a in actual_problems]))),
            Severity(Severity.HIGH),
            Flags([Flags.INHIBITOR]),
            Remediation(commands=[remediation])] + related_resources)
