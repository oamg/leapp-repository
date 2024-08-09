from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import LeftoverPackages, RemovedPackages

FMT_LIST_SEPARATOR = '\n    - '


def process():
    removed_packages = next(api.consume(RemovedPackages), None)
    leftover_packages = next(api.consume(LeftoverPackages), LeftoverPackages())
    leftover_pkgs_to_remove = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in leftover_packages.items]

    if removed_packages and removed_packages.items:
        title = 'Leftover RHEL packages have been removed'
        removed = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in removed_packages.items]
        summary = (
            'Following packages have been removed:{sep}{list}\n'
            'Dependent packages may have been removed as well, please check that you are not missing '
            'any packages.'
            .format(
                sep=FMT_LIST_SEPARATOR,
                list=FMT_LIST_SEPARATOR.join(removed)
            )
        )
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
        ] + [reporting.RelatedResource('package', pkg.name) for pkg in removed_packages.items])
        return

    if leftover_packages and leftover_packages.items:
        summary = (
            'Following RHEL packages have not been upgraded:{sep}{list}'
            'Please remove these packages to keep your system in supported state.'
            .format(
                sep=FMT_LIST_SEPARATOR,
                list=FMT_LIST_SEPARATOR.join(leftover_pkgs_to_remove)
            )
        )
        reporting.create_report([
            reporting.Title('Some RHEL packages have not been upgraded'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
        ] + [reporting.RelatedResource('package', pkg.name) for pkg in leftover_packages.items])
    else:
        api.current_logger().info('No leftover packages, skipping...')
    return
