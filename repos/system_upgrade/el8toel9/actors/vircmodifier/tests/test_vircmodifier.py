import pytest

from leapp.libraries.actor import vircmodifier
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import VircConfig

VIRC_CONTENT = (
    'set nocompatible\n'
    'set history=50\n'
    'filetype plugin on\n'
    'let skip_defaults_vim=1\n'
    'set ruler\n'
)

VIRC_EXPECTED = (
    'set nocompatible\n'
    'set history=50\n'
    'set ruler\n'
)

VIRC_ONLY_FILETYPE = (
    'set nocompatible\n'
    'set history=50\n'
    'filetype plugin on\n'
    'set ruler\n'
)

VIRC_WHITESPACE_CONTENT = (
    'set nocompatible\n'
    'set history=50\n'
    '  filetype plugin on  \n'
    '\tlet skip_defaults_vim=1\t\n'
    'set ruler\n'
)


class MockFile:
    def __init__(self, content=''):
        self.content = content

    def readlines(self):
        return self.content.splitlines(True)

    def writelines(self, lines):
        self.content = ''.join(lines)

    def mock_open(self, path, mode='r'):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_both_lines_removed(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    mock_file = MockFile(VIRC_CONTENT)
    monkeypatch.setattr(vircmodifier, 'open', mock_file.mock_open, raising=False)
    config = VircConfig(path='/etc/virc', lines_to_remove=['filetype plugin on\n', 'let skip_defaults_vim=1\n'])
    vircmodifier.process(iter([config]))
    assert mock_file.content == VIRC_EXPECTED


def test_whitespace_lines_removed(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    mock_file = MockFile(VIRC_WHITESPACE_CONTENT)
    monkeypatch.setattr(vircmodifier, 'open', mock_file.mock_open, raising=False)
    config = VircConfig(
        path='/etc/virc',
        lines_to_remove=['  filetype plugin on  \n', '\tlet skip_defaults_vim=1\t\n']
    )
    vircmodifier.process(iter([config]))
    assert mock_file.content == VIRC_EXPECTED


def test_single_line_removed(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    mock_file = MockFile(VIRC_ONLY_FILETYPE)
    monkeypatch.setattr(vircmodifier, 'open', mock_file.mock_open, raising=False)
    config = VircConfig(path='/etc/virc', lines_to_remove=['filetype plugin on\n'])
    vircmodifier.process(iter([config]))
    assert mock_file.content == VIRC_EXPECTED


def test_empty_lines_to_remove(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    mock_file = MockFile(VIRC_EXPECTED)
    monkeypatch.setattr(vircmodifier, 'open', mock_file.mock_open, raising=False)
    config = VircConfig(path='/etc/virc', lines_to_remove=[])
    vircmodifier.process(iter([config]))
    assert mock_file.content == VIRC_EXPECTED


def test_no_virc_config_message(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    mock_file = MockFile('')
    monkeypatch.setattr(vircmodifier, 'open', mock_file.mock_open, raising=False)
    vircmodifier.process(iter([]))
    assert mock_file.content == ''


def test_read_error(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    mock_file = MockFile(VIRC_CONTENT)

    def _mock_open_error(path, mode='r'):
        raise OSError('Permission denied')

    monkeypatch.setattr(vircmodifier, 'open', _mock_open_error, raising=False)
    config = VircConfig(path='/etc/virc', lines_to_remove=['filetype plugin on\n'])
    vircmodifier.process(iter([config]))
    assert mock_file.content == VIRC_CONTENT
