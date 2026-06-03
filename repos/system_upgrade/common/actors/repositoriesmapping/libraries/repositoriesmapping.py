import os
from collections import defaultdict

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_target_distro_id
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.common.fetch import load_data_asset
from leapp.libraries.common.rpms import get_leapp_packages, LeappComponents
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry, RepoMapEntry, RepositoriesMapping
from leapp.models.fields import ModelViolationError

OLD_REPOMAP_FILE = 'repomap.csv'
"""The name of the old, deprecated repository mapping file (no longer used)."""

REPOMAP_FILE = 'repomap.json'
"""The name of the new repository mapping file."""


class RepoMapData:
    VERSION_FORMAT = '1.4.0'

    def __init__(self):
        self.repositories = []
        self.mapping = {}

    def _add_repository(self, data, pesid):
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

    def _add_mapping(
        self,
        source_major_version,
        target_major_version,
        source_pesid,
        target_pesids,
    ):
        """
        Add a new mapping entry that is mapping the source pesid to the destination pesid(s),
        relevant in an IPU from the supplied source major version to the supplied target
        major version.

        :param str source_major_version: Specifies the major version of the source system
                                         for which the added mapping applies.
        :param str target_major_version: Specifies the major version of the target system
                                         for which the added mapping applies.
        :param str source_pesid: PESID of the source repository.
        :param dict[str, list[str]] target_pesids: A dict mapping distro to a list of PESIDS
        """
        # NOTE: it could be more simple, but I prefer to be sure the input data
        # contains just one map per source PESID.
        key = '{}:{}'.format(source_major_version, target_major_version)
        # source -> distro -> targets
        pesids_map = self.mapping.setdefault(key, defaultdict(lambda: defaultdict(set)))

        for distro, pesids in target_pesids.items():
            pesids_map[source_pesid][distro].update(pesids)

    def get_mappings(self, src_major_version, dst_major_version, dst_distro):
        """
        Return the list of RepoMapEntry objects for the specified upgrade path.

        IOW, the whole mapping for specified IPU.
        """
        key = '{}:{}'.format(src_major_version, dst_major_version)
        pesids_map = self.mapping.get(key, None)
        if not pesids_map:
            return None

        map_list = []
        for src_pesid in sorted(pesids_map.keys()):
            target_pesids_by_distro = pesids_map[src_pesid]
            default = target_pesids_by_distro['default']
            targets = target_pesids_by_distro.get(dst_distro, default)

            map_list.append(RepoMapEntry(source=src_pesid, target=sorted(targets)))

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

        # Load repositories
        existing_pesids = set()
        for repo_family in data['repositories']:
            existing_pesids.add(repo_family['pesid'])
            for repo in repo_family['entries']:
                repomap._add_repository(repo, repo_family['pesid'])

        # Load mappings
        for mapping in data['mapping']:
            for entry in mapping['entries']:
                source_pesid = entry['source']
                target_pesids_by_distro = entry['target']

                if not isinstance(target_pesids_by_distro, dict):
                    raise ValueError(
                        "The 'target' of a mapping entry for PESID {} is {}, must be a dict".format(
                            source_pesid, type(target_pesids_by_distro)
                        )
                    )

                if 'default' not in target_pesids_by_distro:
                    raise ValueError(
                        "The 'target' of a mapping entry for PESID {} does not contain 'default'".format(
                            source_pesid
                        )
                    )

                for _distro, pesids in target_pesids_by_distro.items():
                    if not isinstance(pesids, list):
                        raise ValueError(
                            "Values of the 'target' dict of a mapping entry for PESID {} must be lists".format(
                                source_pesid
                            )
                        )

                for pesid in [entry['source']] + [id for ids in entry['target'].values() for id in ids]:
                    # FIXME: this check isn't complete since the distro field was
                    # introduced for repositories, because the PESID might be
                    # associated with just repositories for a particular
                    # distro(s) and therefore might not be for the source or
                    # target distro.
                    # However this is better than nothing.
                    if pesid not in existing_pesids:
                        raise ValueError(
                            'The {} pesid is not related to any repository.'.format(pesid)
                        )

                repomap._add_mapping(
                    source_major_version=mapping['source_major_version'],
                    target_major_version=mapping['target_major_version'],
                    source_pesid=source_pesid,
                    target_pesids=target_pesids_by_distro,
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


def scan_repositories(read_repofile_func=_read_repofile):
    """
    Scan the repository mapping file and produce RepositoriesMapping msg.

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
        src_ver, dst_ver = get_source_major_version(), get_target_major_version()

        mapping = repomap_data.get_mappings(src_ver, dst_ver, get_target_distro_id())
        if mapping is None:
            # don't really expect this to happen because before it was not
            # handled at all and I am not aware of any crashes
            err_message = (
                'The repository mapping file is invalid: '
                'no mappings found for IPU {}:{}'
            )
            _inhibit_upgrade(err_message.format(src_ver, dst_ver))

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
