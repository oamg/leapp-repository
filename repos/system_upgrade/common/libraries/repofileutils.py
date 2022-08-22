import json
import os

from leapp.libraries.common import mounting, utils
from leapp.libraries.stdlib import api
from leapp.models import fields, RepositoryData, RepositoryFile

try:
    import dnf
except ImportError:
    api.current_logger().warning('repofileutils.py: failed to import dnf')


def _parse_repository(repoid, repo_data):
    def asbool(x):
        return x == '1'
    prepared = {'repoid': repoid, 'additional_fields': {}}
    for key in repo_data.keys():
        if key in RepositoryData.fields:
            if isinstance(RepositoryData.fields[key], fields.Boolean):
                repo_data[key] = asbool(repo_data[key])
            prepared[key] = repo_data[key]
        else:
            prepared['additional_fields'][key] = repo_data[key]
    prepared['additional_fields'] = json.dumps(prepared['additional_fields'])
    return RepositoryData(**prepared)


def parse_repofile(repofile):
    """
    Parse the given repo file.

    :param repofile: Path to the repo file
    :type repofile: str
    :rtype: RepositoryFile
    """
    data = []
    with open(repofile, mode='r') as fp:
        cp = utils.parse_config(fp, strict=False)
        for repoid in cp.sections():
            data.append(_parse_repository(repoid, dict(cp.items(repoid))))
    return RepositoryFile(file=repofile, data=data)


def get_repodirs():
    """
    Return all directories yum scans for repository files, if they exist.
    By default, the possible paths on RHEL should be:
    ['/etc/yum.repos.d', '/etc/yum/repos.d', '/etc/distro.repos.d']

    ATTENTION: Requires the dnf module to be present.
    TODO: Get repodirs inside given context.
    """
    with dnf.base.Base() as base:
        base.conf.read(priority=dnf.conf.PRIO_MAINCONFIG)
        return list({os.path.realpath(d) for d in base.conf.reposdir if os.path.isdir(d)})


def get_parsed_repofiles(context=mounting.NotIsolatedActions(base_dir='/')):
    """
    Scan all repositories on the system.

    Repositories are scanned under repository directories (as reported by dnf)
    of the given context. By default the context is the host system.

    ATTENTION: Do not forget to ensure the redhat.repo file is regenerated
    by RHSM when used.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :rtype: List(RepositoryFile)
    """
    repofiles = []
    cmd = ['find', '-L'] + get_repodirs() + ['-maxdepth', '1', '-type', 'f', '-name', '*.repo']
    repofiles_paths = context.call(cmd, split=True)['stdout']
    for repofile_path in repofiles_paths:
        repofile = parse_repofile(context.full_path(repofile_path))
        # we want full path in cotext, not the real full path
        repofile.file = repofile_path
        repofiles.append(repofile)
    return repofiles


def _invert_dict(data):
    """{a: [b]} -> {b: [a]}"""
    inv_dict = {}
    for key in data.keys():
        for value in data[key]:
            inv_dict[value] = inv_dict.get(value, []) + [key]
    return inv_dict


def get_duplicate_repositories(repofiles):
    """
    Return dict of duplicate repositories {repoid: [repofile_path]}

    A repository is defined multiple times if it exists in multiple repofiles.
    Redefinition inside one repository file is ignored (same in DNF).

    :param repofiles:
    :type repofiles: List(RepositoryFile)
    :rtype: dict {repoid: repofilepath}
    """
    rf_repos = {repofile.file: [repo.repoid for repo in repofile.data] for repofile in repofiles}
    repos = _invert_dict(rf_repos)
    return {repo: set(rfiles) for repo, rfiles in repos.items() if len(set(rfiles)) > 1}
