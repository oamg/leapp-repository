import os

import pytest

from leapp.libraries.common.utils import api, apply_yum_workaround, mounting

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(os.path.join(CUR_DIR, "../"))
    yield
    os.chdir(previous_cwd)


class MockedNotIsolatedActions(object):
    def __init__(self):
        self.called = 0
        self.args = None

    def call(self, args):
        self.called += 1
        self.args = args
        return {'stdout': ''}

    def __call__(self, *args, **kwargs):
        return self


def _get_tool_path(name):
    for directory in os.getenv('LEAPP_COMMON_TOOLS', '').split(':'):
        full_path = os.path.join(directory, name)
        if os.path.isfile(full_path):
            return full_path
    return None


def test_prepare_yum_config(monkeypatch, adjust_cwd):
    actions = MockedNotIsolatedActions()
    monkeypatch.setattr(api, "get_tool_path", _get_tool_path)
    monkeypatch.setattr(mounting, "NotIsolatedActions", actions)
    apply_yum_workaround()
    assert actions.called == 1
    assert os.path.basename(actions.args[-1]) == 'handleyumconfig'
