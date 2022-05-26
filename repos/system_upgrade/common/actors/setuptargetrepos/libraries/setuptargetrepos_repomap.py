from leapp.libraries.common.config import get_target_product_channel
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.stdlib import api

DEFAULT_PESID = {
    '7': 'rhel7-base',
    '8': 'rhel8-BaseOS',
    '9': 'rhel9-BaseOS'
}


def _get_channel_prio(pesid_repo):
    priorities = {
        'beta': 0,
        'ga': 1,
    }
    return priorities.get(pesid_repo.channel, 10)


class RepoMapDataHandler(object):
    """
    Provide the basic functionality to work with the repository data easily.
    """

    def __init__(self, repo_map, cloud_provider='', default_channels=None):
        """
        Initialize the object based on the given RepositoriesMapping msg.

        Expects that msg contains just stuff related for the current IPU
        (at least mapping and repos for the used upgrade path and architecture).

        :param repo_map: A valid RepositoryMapping message.
        :type repo_map: RepositoryMapping
        :param default_channels: A list of default channels to use when a target repository
                                 equivalent exactly matching a source repository was not found.
        :type default_channels: List[str]
        :param prio_channel: Prefer repositories with this channel when looking for target equivalents.
        :type prio_channel: str
        """
        # NOTE: currently I am keeping this default data structure that is not
        # ideal for work, but there is not any significant impact..
        self.repositories = repo_map.repositories
        self.mapping = repo_map.mapping
        # FIXME(pstodulk): what about default_channel -> fallback_channel
        # hardcoded always as ga? instead of list of channels..
        # it'd be possibly confusing naming now...
        self.default_channels = default_channels or ['ga']

        # Make self.prio_channel None if the user did not specify any target channels, so that self.default_channels
        # will be used instead
        self.prio_channel = get_target_product_channel(default=None)

        self.cloud_provider = cloud_provider

        # Cloud provider might have multiple variants, e.g, aws: (aws, aws-sap-es4) - normalize it
        cloud_providers = ('aws', 'azure', 'google')
        for provider in cloud_providers:
            if cloud_provider.startswith(provider):
                self.cloud_provider = provider
                break

    def set_default_channels(self, default_channels):
        """
        Set the default channels that are used as a fallback when searching
        for the right target repository.

        Usually it's not problem to find a target repository that matches
        the source repository, however in some cases the target repository
        doesn't have to be available in the required (premium) channel but
        could be present in the standard one.

        This is used usually for fallbacks and it's prerequisite for the time
        the required channel will not be present for the particular repository.
        E.g. can happen for layered products which has different lifecycles
        and doesn't have to provide a special premium channels at all. E.g.
        the Extras repository has GA and Beta channels, but no EUS. In case the
        EUS is required, returns the GA one instead when this is present.

        It's recommended to make the GA ('ga') always present in the default
        list.

        :param default_channels: Default channels to use when a target equivalent to a source repository that
                                 matches its target channel properties exactly could not be found.
        :type default_channels: List[str]
        """
        self.default_channels = default_channels

    def get_pesid_repo_entry(self, repoid, major_version):
        """
        Retrieve the PESIDRepositoryEntry that matches the given repoid and OS major version.

        If multiple pesid repo entries with the same repoid were found, the entry with rhui matching the source
        system's rhui info will be returned. If no entry with matching rhui exists, the CDN one is returned if any.

        :param repoid: RepoID that should the PESIDRepositoryEntry match.
        :type repoid: str
        :param major_version: RepoID that should the PESIDRepositoryEntry match.
        :type major_version: str
        :return: The PESIDRepositoryEntry matching the given repoid and major_version or None if no such
                 entry could be found.
        :rtype: Optional[PESIDRepositoryEntry]
        """
        matching_pesid_repos = []
        for pesid_repo in self.repositories:
            if pesid_repo.repoid == repoid and pesid_repo.major_version == major_version:
                matching_pesid_repos.append(pesid_repo)

        if len(matching_pesid_repos) == 1:
            # Perform no heuristics if only a single pesid repository with matching repoid found
            return matching_pesid_repos[0]

        # Multiple (different) repositories with the same repoid found (can happen in clouds) - prefer the cloud one
        cdn_pesid_repo = None
        for pesid_repo in matching_pesid_repos:
            if pesid_repo.rhui == self.cloud_provider:
                return pesid_repo
            if not pesid_repo.rhui:
                cdn_pesid_repo = pesid_repo

        # If we did not find a repoid for the current cloud provider, return the CDN repository
        return cdn_pesid_repo  # might be None e.g. if we are on Azure with an AWS repository enabled (unlikely)

    def get_target_pesids(self, source_pesid):
        """
        Return sorted list of target PES IDs for the given source PES ID.

        :param source_pesid: Source PES ID to find equivalents for.
        :type source_pesid: src
        :return: The list of target PES IDs the provided source_pesid is mapped to.
        :rtype: List[PESIDRepositoryEntry]
        """
        pesids = set()
        for repomap in self.mapping:
            if repomap.source == source_pesid:
                pesids.update(repomap.target)
        return sorted(pesids)

    def get_pesid_repos(self, pesid, major_version):
        """
        Get the list of PESIDRepositoryEntry with the specified PES ID and OS major version.

        :param pesid: PES ID of the repositories to be retrieved.
        :type pesid: str
        :param major_version: OS major version of the repositories to be retrieved.
        :type major_version: str
        :return: A list of PESIDRepositoryEntries that match the provided PES ID and OS major version.
        :rtype: List[PESIDRepositoryEntry]
        """
        pesid_repos = []
        for pesid_repo in self.repositories:
            if pesid_repo.pesid == pesid and pesid_repo.major_version == major_version:
                pesid_repos.append(pesid_repo)
        return pesid_repos

    def get_source_pesid_repos(self, pesid):
        """
        Return the list of PESIDRepositoryEntry objects for a specified PES ID
        mathing the source OS major version.

        :param pesid: The PES ID for which to retrieve PESIDRepositoryEntries.
        :type pesid: str
        :return: A list of PESIDRepositoryEntries that match the provided PES ID and have
                 the OS Major version same as the source OS.
        :rtype: List[PESIDRepositoryEntry]
        """
        return self.get_pesid_repos(pesid, get_source_major_version())

    def get_target_pesid_repos(self, pesid):
        """
        Return the list of PESIDRepositoryEntry objects for a specified PES ID
        mathing the target OS major version.

        :param pesid: The PES ID for which to retrieve PESIDRepositoryEntries.
        :type pesid: str
        :return: A list of PESIDRepositoryEntries that match the provided PES ID and have
                 the OS Major version same as the target OS.
        :rtype: List[PESIDRepositoryEntry]
        """
        return self.get_pesid_repos(pesid, get_target_major_version())

    def _find_repository_target_equivalent(self, src_pesidrepo, target_pesid):
        """
        Find the target repository that is the best-match to the source one with the given
        target PES ID.

        :param src_pesidrepo: The source repository to find equivalent to.
        :type src_pesidrepo: PESIDRepositoryEntry
        :param target_pesid: The target PES ID which the target repository must contain.
        :type target_pesid: str
        :return: A target equivalent of given repository.
        :rtype: Optional[PESIDRepositoryEntry]
        """

        candidates = []
        for candidate in self.get_target_pesid_repos(target_pesid):
            matches_rhui = candidate.rhui == src_pesidrepo.rhui
            matches_repo_type = candidate.repo_type == 'rpm'
            matches_arch = candidate.arch == api.current_actor().configuration.architecture

            if matches_rhui and matches_arch and matches_repo_type:
                # user can specify in future the specific channel should be
                # prioritized always (e.g. want to go to EUS...).
                channel = self.prio_channel or src_pesidrepo.channel
                if candidate.channel == channel:
                    return candidate
                candidates.append(candidate)

        # Fallback...
        # Could not find exact-match, so go through candidates if we find an
        # alternative in one of default channels (usually just 'ga')
        for channel in self.default_channels:
            for candidate in candidates:
                if channel == candidate.channel:
                    return candidate

        # This is a case, that must be handled by the caller
        return None

    def get_mapped_target_pesid_repos(self, src_pesidrepo):
        """
        Returns the dict of form {target_pesid: target PESIDRepositoryEntry} containing
        pesids of repositories that is the source pesidrepo mapped to as keys and with
        the best fitting repository for each of the target pesids as values.

        The function always returns the best candidate for every target pesid
        that fits to the given source repository. In case no repository is find
        for a pesid, the value in dict is None: {pesid: None}

        :param src_pesidrepo: The PESIDRepositoryEntry to find the target pesids and the corresponding
                              best-fitting repositories to.
        :type src_pesidrepo: PESIDRepositoryEntry
        :return: A dictionary of the form described above.
        :rtype: Dict[str, PESIDRepositoryEntry]
        """
        result = {}
        for target_pesid in self.get_target_pesids(src_pesidrepo.pesid):
            result[target_pesid] = self._find_repository_target_equivalent(src_pesidrepo, target_pesid)
        return result

    def get_mapped_target_repoids(self, src_pesidrepo):
        """
        Return the list of target repoids for the given src_pesidrepo.

        Some actors do not has to check whether a target repository has been
        found for each target PES ID and details about the target repositories.
        For such actors it's ok to see just list of repoids they should be
        interested about and keep the proper checks for the right actor.

        :param src_pesidrepo: The PESIDRepositoryEntry to find the corresponding best-fitting repositories to.
        :type src_pesidrepo: PESIDRepositoryEntry
        :return: A dictionary of the form described above.
        :rtype: Dict[str, PESIDRepositoryEntry]
        """
        return [repo.repoid for repo in self.get_mapped_target_pesid_repos(src_pesidrepo).values() if repo]

    def get_expected_target_pesid_repos(self, src_repoids):
        """
        Return {target_pesid: PESIDRepositoryEntry} with expected target repositories.

        If some repositories are mapped to a target pesid for which no equivalent
        repository is discovered, such a key contains just None value.

        :param src_repoids: list of present source repoids that should be mapped to target repositories
        :type src_repoids: List[str]
        :rtype: {str: PESIDRepositoryEntry}
        """
        # {pesid: target_repo}
        target_repos_best_candidates = {}
        for src_repoid in src_repoids:
            src_pesidrepo = self.get_pesid_repo_entry(src_repoid, get_source_major_version())
            if not src_pesidrepo:
                # unmapped or custom repo -> skip this one
                continue

            for target_pesid, target_candidate in self.get_mapped_target_pesid_repos(src_pesidrepo).items():
                best_candidate = target_repos_best_candidates.get(target_pesid, None)
                if not best_candidate:
                    # we need to initialize the pesid even when the target_candidate is empty
                    # to know we possibly miss something
                    target_repos_best_candidates[target_pesid] = target_candidate
                if not target_candidate:
                    # It's not crucial in this moment - the pesid can be still filled
                    # by other maps. However log the warning as it is still unexpected
                    # with the valid repomap data
                    api.current_logger().warning(
                        'Cannot find any mapped target repository from the'
                        ' {pesid} family for the {repoid} repository.'
                        .format(repoid=src_repoid, pesid=target_pesid)
                    )
                    continue

                if best_candidate and _get_channel_prio(target_candidate) > _get_channel_prio(best_candidate):
                    # NOTE(pstodulk): we want just one target repository from the "PESID family"
                    # priority: beta < ga < all_else
                    # Why all_else?
                    # -> we do not expect multiple different premium channels present on the system
                    target_repos_best_candidates[target_pesid] = target_candidate
        return target_repos_best_candidates


def get_default_repository_channels(repomap, src_repoids):
    """
    Returns the default repository channels. The 'ga' channel is always included and is the last
    one in the list, so it is the lowest priority when checking for channels.

    :param repomap: A RepoMapDataHandler instance containing the RepositoriesMapping data.
    :type repomap: RepoMapDataHandler
    :param src_repoids: Repositories present on the source system.
    :type src_repoids: List[str]
    :rtype: List[str]
    """
    default_pesid = DEFAULT_PESID[get_source_major_version()]
    top_prio_pesid_repo = None
    for repoid in src_repoids:
        pesid_repo = repomap.get_pesid_repo_entry(repoid, get_source_major_version())
        if not pesid_repo or pesid_repo.pesid != default_pesid:
            continue
        if not top_prio_pesid_repo or _get_channel_prio(pesid_repo) > _get_channel_prio(top_prio_pesid_repo):
            top_prio_pesid_repo = pesid_repo

    # always return at least 'ga'
    if not top_prio_pesid_repo or top_prio_pesid_repo.channel == 'ga':
        return ['ga']

    # keep this order to prefer higher prio to check first
    return [top_prio_pesid_repo.channel, 'ga']
