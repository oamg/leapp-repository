import os

from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, VircConfig

VIRC_CONFIG = '/etc/virc'

LINES_TO_REMOVE = (
    'filetype plugin on',
    'let skip_defaults_vim=1',
)


def _scan_virc(path):
    """
    Read virc and return the original (unstripped) lines whose stripped content
    matches any entry in LINES_TO_REMOVE.
    """
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
    except (OSError, IOError):
        api.current_logger().warning('Could not read {}.'.format(path))
        return []

    return [line for line in lines if line.strip() in LINES_TO_REMOVE]


def process(actor):
    if not has_package(DistributionSignedRPM, 'vim-minimal'):
        api.current_logger().debug('vim-minimal is not installed, skipping virc scan.')
        return

    if not os.path.isfile(VIRC_CONFIG):
        api.current_logger().debug('{} does not exist, skipping virc scan.'.format(VIRC_CONFIG))
        return

    found = _scan_virc(VIRC_CONFIG)
    if not found:
        api.current_logger().debug('No lines to remove found in {}.'.format(VIRC_CONFIG))
        return

    actor.produce(VircConfig(path=VIRC_CONFIG, lines_to_remove=found))

    reporting.create_report([
        reporting.Title('Vim /etc/virc will be updated during upgrade'),
        reporting.Summary(
            'The following lines will be removed from {path} during the upgrade: {lines}'.format(
                path=VIRC_CONFIG,
                lines=', '.join('"{}"'.format(l) for l in found),
            )
        ),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'vim-minimal'),
        reporting.RelatedResource('file', VIRC_CONFIG),
    ])
