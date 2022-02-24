import os

from leapp.libraries.common.dnfplugin import api, apply_workarounds, mounting
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.models import DNFWorkaround


class ShowMessageCurrentActorMocked(CurrentActorMocked):
    def __init__(self, *args, **kwargs):
        super(ShowMessageCurrentActorMocked, self).__init__(*args, **kwargs)
        self._show_messages = []

    @property
    def show_messages(self):
        return self._show_messages

    def show_message(self, message):
        self._show_messages.append(message)


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


def test_prepare_yum_config(monkeypatch):
    actions = MockedNotIsolatedActions()
    monkeypatch.setattr(api, 'get_tool_path', _get_tool_path)
    monkeypatch.setattr(mounting, 'NotIsolatedActions', actions)
    display_name = 'Test Action Handle Yum Config'
    actor = ShowMessageCurrentActorMocked(
        msgs=(
            DNFWorkaround(
                display_name=display_name,
                script_path='/your/path/might/vary/handleyumconfig'
            ),
        ),
    )
    monkeypatch.setattr(api, 'current_actor', actor)
    apply_workarounds()
    assert actions.called == 1
    assert os.path.basename(actions.args[-1]) == 'handleyumconfig'
    assert actor.show_messages and len(actor.show_messages) == 1
    assert display_name in actor.show_messages[0]
