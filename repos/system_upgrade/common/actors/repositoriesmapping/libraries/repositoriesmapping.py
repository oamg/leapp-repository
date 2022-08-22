import json
import os
from collections import defaultdict

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.common.fetch import read_or_fetch
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry, RepoMapEntry, RepositoriesMapping
from leapp.models.fields import ModelViolationError

OLD_REPOMAP_FILE = 'repomap.csv'
"""The name of the old, deprecated repository mapping file (no longer used)."""

REPOMAP_FILE = 'repomap.json'
"""The name of the new repository mapping file."""


class RepoMapData(object):
    VERSION_FORMAT = '1.0.0'

    def __init__(self):
        self.repositories = []
        self.mapping = {}

    def add_repository(self, data, pesid):
        """
        Add new PESIDRepositoryEntry with given pesid from the provided dictionary.

        :param data: A dict containing the data of the added repository. The dictionary structure corresponds
                     to the repositories entries in the repository mapping JSON schema.
        :type data: Dict[str, str]
        :param pesid: PES id of the repository family that the newly added repository belongs to.
        :type pesid: str
        """
        self.repositories.append(PESIDRepositoryEntry(
            repoid=data['repoid'],
            channel=data['channel'],
            rhui=data.get('rhui', ''),
            repo_type=data['repo_type'],
            arch=data['arch'],
            major_version=data['major_version'],
            pesid=pesid
        ))

    def get_repositories(self, valid_major_versions):
        """
        Return the list of PESIDRepositoryEntry object matching the specified major versions.
        """
        return [repo for repo in self.repositories if repo.major_version in valid_major_versions]

    def add_mapping(self, source_major_version, target_major_version, source_pesid, target_pesid):
        """
        Add a new mapping entry that is mapping the source pesid to the destination pesid(s),
        relevant in an IPU from the supplied source major version to the supplied target
        major version.

        :param str source_major_version: Specifies the major version of the source system
                                         for which the added mapping applies.
        :param str target_major_version: Specifies the major version of the target system
                                         for which the added mapping applies.
        :param str source_pesid: PESID of the source repository.
        :param Union[str|List[str]] target_pesid: A single target PESID or a list of target
                                                  PESIDs of the added mapping.
        """
        # NOTE: it could be more simple, but I prefer to be sure the input data
        # contains just one map per source PESID.
        key = '{}:{}'.format(source_major_version, target_major_version)
        rmap = self.mapping.get(key, defaultdict(set))
        self.mapping[key] = rmap
        if isinstance(target_pesid, list):
            rmap[source_pesid].update(target_pesid)
        else:
            rmap[source_pesid].add(target_pesid)

    def get_mappings(self, src_major_version, dst_major_version):
        """
        Return the list of RepoMapEntry objects for the specified upgrade path.

        IOW, the whole mapping for specified IPU.
        """
        key = '{}:{}'.format(src_major_version, dst_major_version)
        rmap = self.mapping.get(key, None)
        if not rmap:
            return None
        map_list = []
        for src_pesid in sorted(rmap.keys()):
            map_list.append(RepoMapEntry(source=src_pesid, target=sorted(rmap[src_pesid])))
        return map_list

    @staticmethod
    def load_from_dict(data):
        if data['version_format'] != RepoMapData.VERSION_FORMAT:
            raise ValueError(
                'The obtained repomap data has unsupported version of format.'
                ' Get {} required {}'
                .format(data['version_format'], RepoMapData.VERSION_FORMAT)
            )

        repomap = RepoMapData()

        # Load reposiories
        existing_pesids = set()
        for repo_family in data['repositories']:
            existing_pesids.add(repo_family['pesid'])
            for repo in repo_family['entries']:
                repomap.add_repository(repo, repo_family['pesid'])

        # Load mappings
        for mapping in data['mapping']:
            for entry in mapping['entries']:
                if not isinstance(entry['target'], list):
                    raise ValueError(
                        'The target field of a mapping entry is not a list: {}'
                        .format(entry)
                    )

                for pesid in [entry['source']] + entry['target']:
                    if pesid not in existing_pesids:
                        raise ValueError(
                            'The {} pesid is not related to any repository.'
                            .format(pesid)
                        )
                repomap.add_mapping(
                    source_major_version=mapping['source_major_version'],
                    target_major_version=mapping['target_major_version'],
                    source_pesid=entry['source'],
                    target_pesid=entry['target'],
                )
        return repomap


def _inhibit_upgrade(msg):
    raise StopActorExecutionError(
        msg,
        details={'hint': ('Read documentation at the following link for more'
                          ' information about how to retrieve the valid file:'
                          ' https://access.redhat.com/articles/3664871')})


def _read_repofile(repofile):
    # NOTE: what about catch StopActorExecution error when the file cannot be
    # obtained -> then check whether old_repomap file exists and in such a case
    # inform user they have to provde the new repomap.json file (we have the
    # warning now only which could be potentially overlooked)
    try:
        return json.loads(read_or_fetch(repofile))
    except ValueError:
        # The data does not contain a valid json
        _inhibit_upgrade('The repository mapping file is invalid: file does not contain a valid JSON object.')
    return None  # Avoids inconsistent-return-statements warning


def scan_repositories(read_repofile_func=_read_repofile):
    """
    Scan the repository mapping file and produce RepositoriesMap msg.

    See the description of the actor for more details.
    """
    # TODO: add filter based on the current arch
    # TODO: deprecate the product type and introduce the "channels" ?.. more or less
    # NOTE: product type is changed, now it's channel: eus,e4s,aus,tus,ga,beta

    if os.path.exists(os.path.join('/etc/leapp/files', OLD_REPOMAP_FILE)):
        # NOTE: what about creating the report (instead of warning)
        api.current_logger().warning(
            'The old repomap file /etc/leapp/files/repomap.csv is present.'
            ' The file has been replaced by the repomap.json file and it is'
            ' not used anymore.'
        )

    json_data = read_repofile_func(REPOMAP_FILE)
    try:
        repomap_data = RepoMapData.load_from_dict(json_data)
        mapping = repomap_data.get_mappings(get_source_major_version(), get_target_major_version())

        valid_major_versions = [get_source_major_version(), get_target_major_version()]
        api.produce(RepositoriesMapping(
            mapping=mapping,
            repositories=repomap_data.get_repositories(valid_major_versions)
        ))
    except ModelViolationError as err:
        err_message = (
            'The repository mapping file is invalid: '
            'the JSON does not match required schema (wrong field type/value): {}'
            .format(err)
        )
        _inhibit_upgrade(err_message)
    except KeyError as err:
        _inhibit_upgrade(
            'The repository mapping file is invalid: the JSON is missing a required field: {}'.format(err))
    except ValueError as err:
        # The error should contain enough information, so we do not need to clarify it further
        _inhibit_upgrade('The repository mapping file is invalid: {}'.format(err))
