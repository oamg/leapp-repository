import os
from collections import defaultdict

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.common.fetch import load_data_asset
from leapp.libraries.common.rpms import get_leapp_packages, LeappComponents
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry, RepoMapEntry, RepositoriesMapping
from leapp.models.fields import ModelViolationError

REPOMAP_FILE = 'repomap.json'
"""The name of the new repository mapping file."""


class RepoMapData:
    VERSION_FORMAT = '1.3.0'

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
            pesid=pesid,
            distro=data['distro'],
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
    local_path = os.path.join('/etc/leapp/file', REPOMAP_FILE)
    hint = (
        'All official data files are nowadays part of the installed rpms.'
        ' This issue is usually encountered when the data files are incorrectly customized, replaced, or removed'
        ' (e.g. by custom scripts).'
        ' In case you want to recover the original {lp} file, remove the current one (if it still exists)'
        ' and reinstall the following packages: {rpms}.'
        .format(
            lp=local_path,
            rpms=', '.join(get_leapp_packages(component=LeappComponents.REPOSITORY))
        )
    )
    raise StopActorExecutionError(msg, details={'hint': hint})


def _read_repofile(repofile):
    # NOTE(pstodulk): load_data_assert raises StopActorExecutionError, see
    # the code for more info. Keeping the handling on the framework in such
    # a case as we have no work to do in such a case here.
    repofile_data = load_data_asset(api.current_actor(),
                                    repofile,
                                    asset_fulltext_name='Repositories mapping',
                                    docs_url='',
                                    docs_title='')
    return repofile_data


def load_repositories_mapping(read_repofile_func=_read_repofile):
    """
    Load the mapping of DNF repositories related to the current upgrade path.

    Read the mapping from the repomap.json file and filter out data irrelevant
    for the current and target system major version.

    Produce and return the RepositoriesMapping message.

    :param read_repofile_func: The function that accept filename string to read the repomap file and return dict
    :type read_repofile_func: Callable[[str], Dict]
    :rtype: RepositoriesMapping
    :raises StopActorExecutionError: When cannot produce valid RepositoriesMapping
    """
    # TODO: add filter based on the current arch

    json_data = read_repofile_func(REPOMAP_FILE)
    try:
        repomap_data = RepoMapData.load_from_dict(json_data)
        mapping = repomap_data.get_mappings(get_source_major_version(), get_target_major_version())

        valid_major_versions = [get_source_major_version(), get_target_major_version()]
        repositories_mapping = RepositoriesMapping(
            mapping=mapping,
            repositories=repomap_data.get_repositories(valid_major_versions)
        )
        api.produce(repositories_mapping)
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

    return repositories_mapping
