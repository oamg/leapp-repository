import os
from io import StringIO

import pytest

from leapp import reporting
from leapp.libraries.actor import vircscanner
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import VircConfig

VIRC_BOTH_LINES = (
    'set nocompatible\n'
    'set history=50\n'
    'filetype plugin on\n'
    'let skip_defaults_vim=1\n'
)

VIRC_ONLY_FILETYPE = (
    'set nocompatible\n'
    'filetype plugin on\n'
    'set history=50\n'
)

VIRC_ONLY_SKIP = (
    'set nocompatible\n'
    'let skip_defaults_vim=1\n'
)

VIRC_NEITHER = (
    'set nocompatible\n'
    'set history=50\n'
)

VIRC_WHITESPACE = (
    '  filetype plugin on  \n'
    '\tlet skip_defaults_vim=1\t\n'
)


class MockActor:
    def __init__(self):
        self.produced = []

    def produce(self, msg):
        self.produced.append(msg)


def _mock_has_package(installed):
    def _has_package(_model, pkg_name):
        return pkg_name in installed
    return _has_package


def _mock_isfile(existing_files):
    def _isfile(path):
        return path in existing_files
    return _isfile


def _mock_open(content):
    def _open(path, mode='r'):
        return StringIO(content)
    return _open


def test_no_vim_minimal(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(vircscanner, 'has_package', _mock_has_package([]))
    actor = MockActor()
    vircscanner.process(actor)
    assert not actor.produced


def test_virc_not_exists(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(vircscanner, 'has_package', _mock_has_package(['vim-minimal']))
    monkeypatch.setattr(os.path, 'isfile', _mock_isfile([]))
    actor = MockActor()
    vircscanner.process(actor)
    assert not actor.produced


def test_both_lines_present(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vircscanner, 'has_package', _mock_has_package(['vim-minimal']))
    monkeypatch.setattr(os.path, 'isfile', _mock_isfile(['/etc/virc']))
    monkeypatch.setattr(vircscanner, 'open', _mock_open(VIRC_BOTH_LINES), raising=False)
    actor = MockActor()
    vircscanner.process(actor)
    assert len(actor.produced) == 1
    msg = actor.produced[0]
    assert isinstance(msg, VircConfig)
    assert len(msg.lines_to_remove) == 2
    assert 'filetype plugin on\n' in msg.lines_to_remove
    assert 'let skip_defaults_vim=1\n' in msg.lines_to_remove


def test_only_filetype(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vircscanner, 'has_package', _mock_has_package(['vim-minimal']))
    monkeypatch.setattr(os.path, 'isfile', _mock_isfile(['/etc/virc']))
    monkeypatch.setattr(vircscanner, 'open', _mock_open(VIRC_ONLY_FILETYPE), raising=False)
    actor = MockActor()
    vircscanner.process(actor)
    assert len(actor.produced) == 1
    assert len(actor.produced[0].lines_to_remove) == 1
    assert 'filetype plugin on\n' in actor.produced[0].lines_to_remove


def test_only_skip_defaults(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vircscanner, 'has_package', _mock_has_package(['vim-minimal']))
    monkeypatch.setattr(os.path, 'isfile', _mock_isfile(['/etc/virc']))
    monkeypatch.setattr(vircscanner, 'open', _mock_open(VIRC_ONLY_SKIP), raising=False)
    actor = MockActor()
    vircscanner.process(actor)
    assert len(actor.produced) == 1
    assert len(actor.produced[0].lines_to_remove) == 1
    assert 'let skip_defaults_vim=1\n' in actor.produced[0].lines_to_remove


def test_neither_line_present(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(vircscanner, 'has_package', _mock_has_package(['vim-minimal']))
    monkeypatch.setattr(os.path, 'isfile', _mock_isfile(['/etc/virc']))
    monkeypatch.setattr(vircscanner, 'open', _mock_open(VIRC_NEITHER), raising=False)
    actor = MockActor()
    vircscanner.process(actor)
    assert not actor.produced


def test_lines_with_whitespace(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vircscanner, 'has_package', _mock_has_package(['vim-minimal']))
    monkeypatch.setattr(os.path, 'isfile', _mock_isfile(['/etc/virc']))
    monkeypatch.setattr(vircscanner, 'open', _mock_open(VIRC_WHITESPACE), raising=False)
    actor = MockActor()
    vircscanner.process(actor)
    assert len(actor.produced) == 1
    assert len(actor.produced[0].lines_to_remove) == 2
