from collections import namedtuple

from leapp import reporting


# Line affected by incompatible NSS configuration
AffectedLine = namedtuple('AffectedLine', 'lineno column module')


def check_modules(lines, blacklist):
    '''
    Find and return all `lines` that contain an item
    from `blacklist` such that the item is not preceded by the # characted,
    which indicates that the item (or whole line) is commented.
    '''
    for lineno, line in enumerate(lines):
        for blacklisted in blacklist:
            comment_index = line.find('#')
            item_index = line.find(blacklisted)
            if item_index > -1:
                if comment_index == -1 or comment_index > item_index:
                    yield AffectedLine(lineno + 1, item_index + 1, blacklisted)


def process_lines(lines, blacklist, config_path):
    modules = []
    for affected in check_modules(lines, blacklist):
        modules.append(
            "- {module} (at line {line})".format(
                line=affected.lineno, module=affected.module
            )
        )

    # configuration is not affected, exit
    if not modules:
        return

    summary = (
        'In-place upgrade cannot proceed due to incompatible NSS (Name Service Switch) configuration.\n'
        'Specifically, the "wins" and "winbind" NSS providers will fail the upgrade\n'
        'transaction due to issues with dynamic linking and the library load order.\n'
    )

    reporting.create_report([
        reporting.Title("Incompatible NSS configuration"),
        reporting.Summary(summary + '\n'.join(modules)),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Flags([reporting.Flags.INHIBITOR]),
        reporting.ExternalLink(
            'https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/upgrading_to_rhel_8/troubleshooting_upgrading-to-rhel-8#known-issues-upgrading-to-rhel-8',  # noqa: E501; pylint: disable=line-too-long
            'Samba/NSS linkage problem article'
        ),
        reporting.RelatedResource('file', config_path)
    ])
