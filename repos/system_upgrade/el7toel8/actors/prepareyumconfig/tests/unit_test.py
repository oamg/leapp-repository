import os

import leapp.libraries.stdlib


class run_mocked(object):
    def __init__(self):
        self.called = 0
        self.args = None

    def __call__(self, args, split=False):
        self.called += 1
        self.args = args
        return {'stdout': ''}


def _get_tool_path(name):
    for directory in os.getenv('LEAPP_COMMON_TOOLS', '').split(':'):
        full_path = os.path.join(directory, name)
        if os.path.isfile(full_path):
            return full_path
    return None


def test_prepare_yum_config(monkeypatch):
    run = run_mocked()
    with monkeypatch.context() as context:
        context.setattr(leapp.libraries.stdlib, 'run', run)
        context.setattr(leapp.libraries.stdlib.api, 'get_tool_path', _get_tool_path)
        from leapp.libraries.common import utils  # Needed locally to allow monkey patching to actually work
        utils.apply_yum_workaround()
    assert run.called == 1
    assert os.path.basename(run.args[-1]) == 'handleyumconfig'
