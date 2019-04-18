import os

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api
from leapp.libraries.stdlib.config import is_verbose
from leapp.models import InstalledUnsignedRPM


def skip_check():
    """ Check if has environment variable to skip this actor checks """
    if os.getenv('LEAPP_SKIP_CHECK_SIGNED_PACKAGES'):
        reporting.report_generic(title='Skipped signed packages check',
                                 severity='low',
                                 summary='Signed packages check skipped via LEAPP_SKIP_CHECK_SIGNED_PACKAGES env var')
        raise StopActorExecution()


def generate_report(packages):
    """ Generate a report if exists packages unsigned in the system """
    if not len(packages):
        return
    unsigned_packages_new_line = '\n'.join(['- ' + p for p in packages])
    unsigned_packages = ' '.join(packages)
    remediation = 'yum remove {}'.format(unsigned_packages)
    summary = 'The following packages have not been signed by Red Hat ' \
              'and may be removed in the upgrade process:\n{}'.format(unsigned_packages_new_line)
    reporting.report_with_remediation(
        title='Packages not signed by Red Hat found in the system',
        summary=summary,
        remediation=remediation,
        severity='high',
    )
    if is_verbose():
        api.show_message(summary)


def get_unsigned_packages():
    """ Get list of unsigned packages installed in the system """
    rpm_messages = api.consume(InstalledUnsignedRPM)
    data = next(rpm_messages, InstalledUnsignedRPM())
    if list(rpm_messages):
        api.current_logger().warning('Unexpectedly received more than one InstalledUnsignedRPM message.')
    unsigned_packages = set()
    unsigned_packages.update([pkg.name for pkg in data.items])
    unsigned_packages = list(unsigned_packages)
    unsigned_packages.sort()
    return unsigned_packages


def check_unsigned_packages():
    """ Check and generate reports if system contains unsigned installed packages"""
    generate_report(get_unsigned_packages())
