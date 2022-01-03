from leapp.actors import Actor
from leapp.libraries.common.rpms import get_installed_rpms
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

class CheckRemovedPackages(Actor):
    """
    Check for packages that have been removed between RHEL-8 and RHEL-9.
    Inhibit the upgrade process if any of them is installed on the system.
    """

    name = 'check_removed_packages'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        REMOVED_PACKAGES = {'compat-openssl10', 'fipscheck', 'openssh-cavs', 'openssh-ldap',
                            'pinentry-emacs', 'pinentry-gtk', 'pyopenssl'}
        leftover_packages = REMOVED_PACKAGES.intersection(set(get_installed_rpms()))

        if leftover_packages:
            create_report([
                reporting.Title('Leftover RHEL-8 packages'),
                reporting.Summary('Following packages have been removed in RHEL-9:\n{}'.format('\n'.join(leftover_packages))),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Tags([reporting.Tags.SANITY]),
                reporting.Flags([reporting.Flags.INHIBITOR])
            ])

