from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api, format_list
from leapp.models import LeftoverPackages, RemovedPackages


def process():
    removed_packages = next(api.consume(RemovedPackages), None)
    leftover_packages = next(api.consume(LeftoverPackages), LeftoverPackages())
    leftover_pkgs_to_remove = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in leftover_packages.items]

    if removed_packages and removed_packages.items:
        title = 'Leftover packages from the original OS have been removed'
        removed = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in removed_packages.items]
        summary = (
            'Following {source_distro} packages have been removed:{list}\n'
            'Dependent packages may have been removed as well, please check that you are not missing '
            'any packages.'
            .format(
                list=format_list(removed),
                **DISTRO_REPORT_NAMES
            )
        )
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Key('5afbad560709afa4e40a160e40dfd44788ba9c3b'),
        ] + [reporting.RelatedResource('package', pkg.name) for pkg in removed_packages.items])
        return

    if leftover_packages and leftover_packages.items:
        summary = (
            'Following {source_distro} packages have not been upgraded:{list}\n'
            'Please remove these packages to keep your system in supported state.'
            .format(
                list=format_list(leftover_pkgs_to_remove),
                **DISTRO_REPORT_NAMES
            )
        )
        reporting.create_report([
            reporting.Title('Some packages from the original OS have not been upgraded'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Key('d424c3132ed78a8632b5c73d919909e453107c06'),
        ] + [reporting.RelatedResource('package', pkg.name) for pkg in leftover_packages.items])
    else:
        api.current_logger().info('No leftover packages, skipping...')
    return
