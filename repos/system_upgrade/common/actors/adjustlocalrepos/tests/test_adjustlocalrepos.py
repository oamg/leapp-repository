import pytest

from leapp.libraries.actor import adjustlocalrepos

REPO_FILE_1_LOCAL_REPOIDS = ['myrepo1']
REPO_FILE_1 = [['[myrepo1]',
                'name=mylocalrepo',
                'baseurl=file:///home/user/.local/myrepos/repo1'
                ]]
REPO_FILE_1_ADJUSTED = [['[myrepo1]',
                         'name=mylocalrepo',
                         'baseurl=file:///installroot/home/user/.local/myrepos/repo1'
                         ]]

REPO_FILE_2_LOCAL_REPOIDS = ['myrepo3']
REPO_FILE_2 = [['[myrepo2]',
                'name=mynotlocalrepo',
                'baseurl=https://www.notlocal.com/packages'
                ],
               ['[myrepo3]',
                'name=mylocalrepo',
                'baseurl=file:///home/user/.local/myrepos/repo3',
                'mirrorlist=file:///home/user/.local/mymirrors/repo3.txt'
                ]]
REPO_FILE_2_ADJUSTED = [['[myrepo2]',
                         'name=mynotlocalrepo',
                         'baseurl=https://www.notlocal.com/packages'
                         ],
                        ['[myrepo3]',
                         'name=mylocalrepo',
                         'baseurl=file:///installroot/home/user/.local/myrepos/repo3',
                         'mirrorlist=file:///installroot/home/user/.local/mymirrors/repo3.txt'
                         ]]

REPO_FILE_3_LOCAL_REPOIDS = ['myrepo4', 'myrepo5']
REPO_FILE_3 = [['[myrepo4]',
                'name=myrepowithlocalgpgkey',
                'baseurl="file:///home/user/.local/myrepos/repo4"',
                'gpgkey=file:///home/user/.local/pki/gpgkey',
                'gpgcheck=1'
                ],
               ['[myrepo5]',
                'name=myrepowithcomment',
                'baseurl=file:///home/user/.local/myrepos/repo5',
                '#baseurl=file:///home/user/.local/myotherrepos/repo5',
                'enabled=1',
                'exclude=sed']]
REPO_FILE_3_ADJUSTED = [['[myrepo4]',
                         'name=myrepowithlocalgpgkey',
                         'baseurl=file:///installroot/home/user/.local/myrepos/repo4',
                         'gpgkey=file:///home/user/.local/pki/gpgkey',
                         'gpgcheck=1'
                         ],
                        ['[myrepo5]',
                         'name=myrepowithcomment',
                         'baseurl=file:///installroot/home/user/.local/myrepos/repo5',
                         '#baseurl=file:///home/user/.local/myotherrepos/repo5',
                         'enabled=1',
                         'exclude=sed']]
REPO_FILE_EMPTY = []


@pytest.mark.parametrize('repo_file_line, expected_adjusted_repo_file_line',
                         [('baseurl=file:///home/user/.local/repositories/repository',
                           'baseurl=file:///installroot/home/user/.local/repositories/repository'),
                          ('baseurl="file:///home/user/my-repo"',
                           'baseurl=file:///installroot/home/user/my-repo'),
                          ('baseurl=https://notlocal.com/packages',
                           'baseurl=https://notlocal.com/packages'),
                          ('mirrorlist=file:///some_mirror_list.txt',
                           'mirrorlist=file:///installroot/some_mirror_list.txt'),
                          ('gpgkey=file:///etc/pki/some.key',
                           'gpgkey=file:///etc/pki/some.key'),
                          ('#baseurl=file:///home/user/my-repo',
                           '#baseurl=file:///home/user/my-repo'),
                          ('', ''),
                          ('[repoid]', '[repoid]')])
def test_adjust_local_file_url(repo_file_line, expected_adjusted_repo_file_line):
    adjusted_repo_file_line = adjustlocalrepos._adjust_local_file_url(repo_file_line)
    if 'file://' not in repo_file_line:
        assert adjusted_repo_file_line == repo_file_line
        return
    assert adjusted_repo_file_line == expected_adjusted_repo_file_line


class MockedFileDescriptor(object):

    def __init__(self, repo_file, expected_new_repo_file):
        self.repo_file = repo_file
        self.expected_new_repo_file = expected_new_repo_file

    @staticmethod
    def _create_repo_file_lines(repo_file):
        repo_file_lines = []
        for repo in repo_file:
            repo = [line+'\n' for line in repo]
            repo_file_lines += repo
        return repo_file_lines

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return

    def readlines(self):
        return self._create_repo_file_lines(self.repo_file)

    def write(self, new_contents):
        assert self.expected_new_repo_file
        repo_file_lines = self._create_repo_file_lines(self.expected_new_repo_file)
        expected_repo_file_contents = ''.join(repo_file_lines).rstrip('\n')
        assert expected_repo_file_contents == new_contents


class MockedContext(object):

    def __init__(self, repo_contents, expected_repo_contents):
        self.repo_contents = repo_contents
        self.expected_repo_contents = expected_repo_contents

    def open(self, path, mode):
        return MockedFileDescriptor(self.repo_contents, self.expected_repo_contents)


@pytest.mark.parametrize('repo_file, local_repoids, expected_repo_file',
                         [(REPO_FILE_1, REPO_FILE_1_LOCAL_REPOIDS, REPO_FILE_1_ADJUSTED),
                          (REPO_FILE_2, REPO_FILE_2_LOCAL_REPOIDS, REPO_FILE_2_ADJUSTED),
                          (REPO_FILE_3, REPO_FILE_3_LOCAL_REPOIDS, REPO_FILE_3_ADJUSTED)])
def test_adjust_local_repos_to_container(repo_file, local_repoids, expected_repo_file):
    # The checks for expected_repo_file comparison to a adjusted form of the
    # repo_file can be found in the MockedFileDescriptor.write().
    context = MockedContext(repo_file, expected_repo_file)
    adjustlocalrepos._adjust_local_repos_to_container(context, '<some_repo_file_path>', local_repoids)


@pytest.mark.parametrize('expected_repo_file, add_empty_lines', [(REPO_FILE_EMPTY, False),
                                                                 (REPO_FILE_1, False),
                                                                 (REPO_FILE_2, True)])
def test_extract_repos_from_repofile(expected_repo_file, add_empty_lines):
    repo_file = expected_repo_file[:]
    if add_empty_lines:  # add empty lines before the first repo
        repo_file[0] = ['', ''] + repo_file[0]

    context = MockedContext(repo_file, None)
    repo_gen = adjustlocalrepos._extract_repos_from_repofile(context, '<some_repo_file_path>')

    for repo in expected_repo_file:
        assert repo == next(repo_gen, None)

    assert next(repo_gen, None) is None
