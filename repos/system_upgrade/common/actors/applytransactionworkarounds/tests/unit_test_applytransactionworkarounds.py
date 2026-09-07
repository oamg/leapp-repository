import os

from leapp.libraries.common.dnflibs.dnfplugin import api, apply_workarounds, mounting
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.models import DNFWorkaround


class ShowMessageCurrentActorMocked(CurrentActorMocked):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._show_messages = []

    @property
    def show_messages(self):
        return self._show_messages

    def show_message(self, message):
        self._show_messages.append(message)


class MockedNotIsolatedActions:
    def __init__(self):
        self.called = 0
        self.args = None

    def call(self, args):
        self.called += 1
        self.args = args
        return {'stdout': ''}

    def __call__(self, *args, **kwargs):
        return self


class MockedContext:
    """Records makedirs/copy_to/call so we can assert what ran where."""

    def __init__(self):
        self.calls = []
        self.makedirs_paths = []
        self.copied = []

    def call(self, args):
        self.calls.append(args)
        return {'stdout': ''}

    def makedirs(self, path):
        self.makedirs_paths.append(path)

    def copy_to(self, src, dst):
        self.copied.append((src, dst))


_CONTAINER_SCRIPTS_DIR = '/var/tmp/dnf_workaround_scripts'


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


def test_apply_workarounds_host_context_runs_on_host(monkeypatch):
    host = MockedContext()
    container = MockedContext()
    actor = ShowMessageCurrentActorMocked(
        msgs=(
            # execution_context defaults to 'host'
            DNFWorkaround(display_name='host wa', script_path='/path/to/hostscript'),
        ),
    )
    monkeypatch.setattr(api, 'current_actor', actor)

    apply_workarounds(host, container)

    # host workaround runs on the host context with its path untouched, nothing copied
    assert host.calls == [['/bin/bash', '-c', '/path/to/hostscript']]
    assert not container.calls
    assert not host.copied and not host.makedirs_paths


def test_apply_workarounds_container_context_copies_and_runs_in_container(monkeypatch):
    host = MockedContext()
    container = MockedContext()
    actor = ShowMessageCurrentActorMocked(
        msgs=(
            DNFWorkaround(
                display_name='container wa',
                script_path='/path/to/containerscript',
                execution_context='container',
            ),
        ),
    )
    monkeypatch.setattr(api, 'current_actor', actor)

    apply_workarounds(host, container)

    # the script is copied into the container scripts dir and executed there,
    # using the copied path, on the container context - never on the host
    assert not host.calls
    assert container.makedirs_paths == [_CONTAINER_SCRIPTS_DIR]
    assert container.copied == [('/path/to/containerscript', _CONTAINER_SCRIPTS_DIR)]
    expected_path = os.path.join(_CONTAINER_SCRIPTS_DIR, 'containerscript')
    assert container.calls == [['/bin/bash', '-c', expected_path]]


def test_apply_workarounds_appends_script_args(monkeypatch):
    host = MockedContext()
    actor = ShowMessageCurrentActorMocked(
        msgs=(
            DNFWorkaround(
                display_name='wa with args',
                script_path='/path/to/script',
                script_args=['--foo', 'bar'],
            ),
        ),
    )
    monkeypatch.setattr(api, 'current_actor', actor)

    apply_workarounds(host, MockedContext())

    assert host.calls == [['/bin/bash', '-c', '/path/to/script --foo bar']]
