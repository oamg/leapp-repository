import os

from leapp.libraries.stdlib import api

HOST_ROOT_MOUNT_BIND_PATH = '/installroot'
LOCAL_FILE_URL_PREFIX = 'file://'


def _adjust_local_file_url(repo_file_line):
    """
    Adjusts a local file url to the target user-space container in a provided
    repo file line by prefixing host root mount bind '/installroot' to it
    when needed.

    :param str repo_file_line: a line from a repo file
    :returns str: adjusted line or the provided line if no changes are needed
    """
    adjust_fields = ['baseurl', 'mirrorlist']

    if LOCAL_FILE_URL_PREFIX in repo_file_line and not repo_file_line.startswith('#'):
        entry_field, entry_value = repo_file_line.strip().split('=', 1)
        if not any(entry_field.startswith(field) for field in adjust_fields):
            return repo_file_line

        entry_value = entry_value.strip('\'\"')
        path = entry_value[len(LOCAL_FILE_URL_PREFIX):]
        new_entry_value = LOCAL_FILE_URL_PREFIX + os.path.join(HOST_ROOT_MOUNT_BIND_PATH, path.lstrip('/'))
        new_repo_file_line = entry_field + '=' + new_entry_value
        return new_repo_file_line
    return repo_file_line


def _extract_repos_from_repofile(context, repo_file):
    """
    Generator function that extracts repositories from a repo file in the given context
    and yields them as list of lines that belong to the repository.

    :param context: target user-space context
    :param str repo_file: path to repository file (inside the provided context)
    """
    with context.open(repo_file, 'r') as rf:
        repo_file_lines = rf.readlines()

    # Detect repo and remove lines before first repoid
    repo_found = False
    for idx, line in enumerate(repo_file_lines):
        if line.startswith('['):
            repo_file_lines = repo_file_lines[idx:]
            repo_found = True
            break

    if not repo_found:
        return

    current_repo = []
    for line in repo_file_lines:
        line = line.strip()

        if line.startswith('[') and current_repo:
            yield current_repo
            current_repo = []

        current_repo.append(line)
    yield current_repo


def _adjust_local_repos_to_container(context, repo_file, local_repoids):
    new_repo_file = []
    for repo in _extract_repos_from_repofile(context, repo_file):
        repoid = repo[0].strip('[]')
        adjusted_repo = repo
        if repoid in local_repoids:
            adjusted_repo = [_adjust_local_file_url(line) for line in repo]
        new_repo_file.append(adjusted_repo)

    # Combine the repo file contents into a string and write it back to the file
    new_repo_file = ['\n'.join(repo) for repo in new_repo_file]
    new_repo_file = '\n'.join(new_repo_file)
    with context.open(repo_file, 'w') as rf:
        rf.write(new_repo_file)


def process(context, target_repos_facts, iso_repoids, used_target_repoids):
    for repo_file_facts in target_repos_facts:
        repo_file_path = repo_file_facts.file
        local_repoids = set()
        for repo in repo_file_facts.data:
            # Skip repositories that aren't used or are provided by ISO
            if repo.repoid not in used_target_repoids or repo.repoid in iso_repoids:
                continue
            # Note repositories that contain local file url
            if repo.baseurl and LOCAL_FILE_URL_PREFIX in repo.baseurl or \
               repo.mirrorlist and LOCAL_FILE_URL_PREFIX in repo.mirrorlist:
                local_repoids.add(repo.repoid)

        if local_repoids:
            api.current_logger().debug(
                    'Adjusting following repos in the repo file - {}: {}'.format(repo_file_path,
                                                                                 ', '.join(local_repoids)))
            _adjust_local_repos_to_container(context, repo_file_path, local_repoids)
