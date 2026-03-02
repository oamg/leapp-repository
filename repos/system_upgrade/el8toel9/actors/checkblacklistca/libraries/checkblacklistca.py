from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api
from leapp.models import BlackListCA, BlackListError


# just like replace except it starts from the back
# of the string
def rreplace(s, old, new, count):
    return s[::-1].replace(old[::-1], new[::-1], count)[::-1]


def process():
    moving = {}
    commaTarget = {}
    deleting = []
    # process all the BlackListCA events into a single report
    # first collect all the files moving to the same target.
    # as well as any source directories that will be deleted
    for ca in api.consume(BlackListCA):
        if ca.targetDir not in commaTarget:
            commaTarget[ca.targetDir] = ''
        if ca.targetDir not in moving:
            moving[ca.targetDir] = ''
        moving[ca.targetDir] = moving[ca.targetDir] + commaTarget[ca.targetDir] + ca.source
        commaTarget[ca.targetDir] = ', '
        if ca.sourceDir not in deleting:
            deleting.append(ca.sourceDir)

    # now make our lists of files and targets into a single string
    comma = ''
    reportString = ''
    for key in moving:
        # replace the last ', ' with ' and '
        moveString = rreplace(moving[key], ', ', ' and ', 1)
        reportString = reportString + comma + "{} will be moved to {}".format(moveString, key)
        comma = ': '
    reportString = rreplace(reportString, ': ', ' and ', 1).replace(': ', ', ')

    # finally make a string our of the removed directories
    comma = ''
    deleteString = ''
    for d in deleting:
        deleteString = deleteString + comma + d
        comma = ', '
    deleteString = rreplace(deleteString, ', ', ' and ', 1)

    # finally make a string of the
    if moving:
        reporting.create_report([
            reporting.Title('Distrusted CA certificates will be moved from blacklist to blocklist'),
            reporting.Summary(
                'The directories which store user and administrator supplied '
                'distrusted certificates were renamed from blacklist in '
                '{source_distro} 8 to blocklist in {target_distro} 9. '
                'As a result {report_strin} and {delete_string} will be deleted.'.format(
                    report_string=reportString,
                    delete_string=deleteString,
                    **DISTRO_REPORT_NAMES,
                )
            ),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.SECURITY]),
            reporting.Groups([reporting.Groups.AUTHENTICATION])
        ])
    for ble in api.consume(BlackListError):
        reporting.create_report([
            reporting.Title('Could not access blacklist directory'),
            reporting.Summary(
                'The directories which stores user and administrator supplied '
                'distrusted certificates has change names from blacklist in '
                '{source_distro} 8 to blocklist in {target_distro} 9. '
                'But we are unable to access the {source_distro} 8 directory '
                '{source_dir} because {error}. You can clear this error by '
                'correcting the condition, or by moving the contents to '
                '{target_dir} and removing {source_dir} completely'.format(
                    source_dir=ble.sourceDir,
                    error=ble.error,
                    target_dir=ble.targetDir,
                    **DISTRO_REPORT_NAMES,
                )
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SECURITY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.AUTHENTICATION])
        ])
