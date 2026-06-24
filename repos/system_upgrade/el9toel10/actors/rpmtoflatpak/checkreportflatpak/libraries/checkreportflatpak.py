from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import RpmToFlatpakFacts


def process():
    facts = next(api.consume(RpmToFlatpakFacts), None)
    if not facts or not facts.packages:
        return

    rpm_names = sorted(p.rpm_name for p in facts.packages)
    pkg_list = ', '.join(rpm_names)

    summary = (
        'The following packages are installed as RPMs but are no longer shipped as RPMs '
        'on the target system. They will be migrated to their Flatpak equivalents '
        'during the upgrade: {packages}.\n\n'
        'The migration is performed by installing the corresponding '
        'redhat-flatpak-preinstall-* packages on the target system and running '
        '`flatpak preinstall`.'
    ).format(packages=pkg_list)

    reporting.create_report([
        reporting.Title(
            'RPM packages will be migrated to Flatpak: {}'.format(pkg_list)
        ),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
    ])
