import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import config
from leapp.libraries.stdlib import api
from leapp.models import RepositoriesMap, RepositoryMap
from leapp.models.fields import ModelViolationError

REPOMAP_FILE = '/etc/leapp/files/repomap.csv'
"""Path to the repository mapping file."""


def _inhibit_upgrade(msg):
    raise StopActorExecutionError(
        msg,
        details={'hint': ('Read documentation at the following link for more'
                          ' information about how to retrieve the valid file:'
                          ' https://access.redhat.com/articles/3664871')})


def _read_repofile(path):
    if not os.path.isfile(path):
        _inhibit_upgrade('The repository mapping file not found ({}).'.format(path))

    if os.path.getsize(path) == 0:
        _inhibit_upgrade('The repository mapping file is invalid ({}).'.format(path))

    with open(path) as fp:
        return [line.strip() for line in fp.readlines()]


def scan_repositories(read_repofile_func=_read_repofile):
    """
    Scan the repository mapping file and produce RepositoriesMap msg.

    See the description of the actor for more details.
    """
    _exp_src_prod_type = config.get_product_type('source')
    _exp_dst_prod_type = config.get_product_type('target')

    repositories = []
    line_num = 0
    for line in read_repofile_func(REPOMAP_FILE)[1:]:
        line_num += 1

        # skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        try:
            (from_repoid, to_repoid, to_pes_repo,
             from_minor_version, to_minor_version, arch,
             repo_type, src_prod_type, dst_prod_type) = line.split(',')

            # filter out records irrelevant for this run
            if (arch != api.current_actor().configuration.architecture
                    or _exp_src_prod_type != src_prod_type
                    or _exp_dst_prod_type != dst_prod_type):
                continue

            repositories.append(
                RepositoryMap(
                    from_repoid=from_repoid,
                    to_repoid=to_repoid,
                    to_pes_repo=to_pes_repo,
                    from_minor_version=from_minor_version,
                    to_minor_version=to_minor_version,
                    arch=arch,
                    repo_type=repo_type,
                )
            )
        except (ModelViolationError, ValueError) as err:
            _inhibit_upgrade('The repository mapping file is invalid, offending line number: {} ({}).'
                             ' It is possible the file is out of date.'
                             .format(line_num, err))

    if not repositories:
        _inhibit_upgrade('The repository mapping file is invalid. Could not find any repository mapping record.')

    api.produce(RepositoriesMap(repositories=repositories))
