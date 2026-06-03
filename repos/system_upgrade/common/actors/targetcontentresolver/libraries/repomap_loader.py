import os
from collections import defaultdict

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.common.fetch import load_data_asset
from leapp.libraries.common.rpms import get_leapp_packages, LeappComponents
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry, RepoMapEntry, RepositoriesMapping
from leapp.models.fields import ModelViolationError

REPOMAP_FILE = 'repomap.json'
"""The name of the new repository mapping file."""


class RepoMapData:
    VERSION_FORMAT = '2.0.0'

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

    def get_repositories(self, major_versions, distros, arches):
        """
        Get repository entries for the specified major versions and distros

        :return: PESIDRepositoryEntry objects matching the specified major versions, distros and arches
        :rtype: list[PESIDRepositoryEntry]
        """
        return [
            repo
            for repo in self.repositories
            if repo.major_version in major_versions
            and repo.distro in distros
            and repo.arch in arches
        ]

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

    def validate_target_pesids_for_ipu(self, source_distro, target_distro, arch):
        """
        Validate that all PESIDs are associated with a repository

        If a PESID is mapped as a target PESID in the mapping section, check
        that the PESID is associated with some repository for the given IPU
        i.e. a repository matching the given source and target distro and
        architecture and the target major version exists in the repositories
        section.

        The check doesn't really make sense for a PESID mapped as a source,
        because it not being present in repositories section for the given IPU
        can be intentional and is valid.
        """
        # TODO maybe take into account just the current source/target version?
        # But we can check them without further input unlike the distro and
        # arch.
        repo_lookup = set()
        for repo in self.repositories:
            repo_lookup.add((repo.pesid, repo.major_version, repo.distro, repo.arch))

        for upg_path, mappings in self.mapping.items():
            source_ver, target_ver = upg_path.split(':', 1)

            for source_pesid, target_pesids_by_distro in mappings.items():
                default = target_pesids_by_distro['default']
                pesids_for_distro = target_pesids_by_distro.get(target_distro, default)

                # There is no repository for the source system that would belong to the pesid
                # that is the source of the mapping. Therefore, the mapping will never be used
                # and we can skip checking its target pesids. This avoids raising ValueErrors,
                # for example, for on RHUI-mappings that will be always defined only for RHEL.
                if (source_pesid, source_ver, source_distro, arch) not in repo_lookup:
                    continue

                for pesid in pesids_for_distro:
                    if (pesid, target_ver, target_distro, arch) not in repo_lookup:
                        raise ValueError(
                            "Target PESID {} does not have any associated repository"
                            " for major version {} and distro {}.".format(
                                pesid,
                                target_ver,
                                target_distro,
                            )
                        )

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
                    # NOTE: this check isn't complete for target repositories,
                    # since the distro field was introduced for repositories,
                    # because the PESID might be associated with just
                    # repositories for a particular distro(s) and therefore
                    # might not be for the target distro.
                    # This is therefore a very simple check, for a proper one
                    # the :py:func:`validate_target_pesids_for_ipu` can be
                    # used.
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


def load_repositories_mapping(read_repofile_func=_read_repofile):
    """
    Load the mapping of DNF repositories related to the current upgrade path.

    Read the mapping from the repomap.json file and filter out data irrelevant
    for the current and target system major version and distribution.

    Produce and return the RepositoriesMapping message.

    :param read_repofile_func: The function that accept filename string to read the repomap file and return dict
    :type read_repofile_func: Callable[[str], Dict]
    :rtype: RepositoriesMapping
    :raises StopActorExecutionError: When cannot produce valid RepositoriesMapping
    """

    json_data = read_repofile_func(REPOMAP_FILE)
    try:
        repomap_data = RepoMapData.load_from_dict(json_data)

        src_distro, dst_distro = get_source_distro_id(), get_target_distro_id()
        src_ver, dst_ver = get_source_major_version(), get_target_major_version()
        arch = api.current_actor().configuration.architecture

        repomap_data.validate_target_pesids_for_ipu(src_distro, dst_distro, arch)

        mapping = repomap_data.get_mappings(src_ver, dst_ver, dst_distro)
        if mapping is None:
            # don't really expect this to happen because before it was not
            # handled at all and I am not aware of any crashes
            err_message = (
                'The repository mapping file is invalid: '
                'no mappings found for IPU {}:{}'
            )
            _inhibit_upgrade(err_message.format(src_ver, dst_ver))

        repos = repomap_data.get_repositories(
            [src_ver, dst_ver],
            [src_distro, dst_distro],
            [arch],
        )

        repositories_mapping = RepositoriesMapping(mapping=mapping, repositories=repos)
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
