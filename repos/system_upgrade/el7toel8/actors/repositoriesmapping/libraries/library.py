import csv
import os

from leapp.exceptions import StopActorExecution
from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import RepositoriesMap, RepositoryMap
from leapp.models.fields import ModelViolationError


def inhibit_upgrade(title):
    summary = 'Read documentation at: https://access.redhat.com/articles/3664871 for more information ' \
        'about how to retrieve the files'
    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Tags([reporting.Tags.UPGRADE_PROCESS]),
        reporting.Flags([reporting.Flags.INHIBITOR])
    ])
    raise StopActorExecution()


def scan_repositories(path):
    if not os.path.isfile(path):
        inhibit_upgrade('Repositories map file not found ({})'.format(path))

    if os.path.getsize(path) == 0:
        inhibit_upgrade('Repositories map file is invalid ({})'.format(path))

    repositories = []
    with open(path) as f:
        data = csv.reader(f)
        next(data)  # skip header

        for row in data:
            # skip empty lines and comments
            if not row or row[0].startswith('#'):
                continue

            try:
                from_id, to_id, from_minor_version, to_minor_version, arch, repo_type = row
            except ValueError as err:
                inhibit_upgrade('Repositories map file is invalid, offending line number: {} ({})'.format(
                    data.line_num, err))

            try:
                repositories.append(RepositoryMap(from_id=from_id,
                                                  to_id=to_id,
                                                  from_minor_version=from_minor_version,
                                                  to_minor_version=to_minor_version,
                                                  arch=arch,
                                                  repo_type=repo_type))
            except ModelViolationError as err:
                inhibit_upgrade('Repositories map file is invalid, offending line number: {} ({})'.format(
                    data.line_num, err))

    if not repositories:
        inhibit_upgrade('Repositories map file is invalid ({})'.format(path))

    api.produce(RepositoriesMap(repositories=repositories))
