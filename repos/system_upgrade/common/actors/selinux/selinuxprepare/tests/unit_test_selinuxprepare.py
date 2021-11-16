from leapp.libraries.actor import selinuxprepare
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SELinuxModule, SELinuxModules


class run_mocked(object):
    def __init__(self):
        self.args = []
        self.called = 0
        self.removed_modules = set()
        self.non_semodule_calls = 0

    def __call__(self, args, split=True):
        self.called += 1
        self.args = args

        if self.args[0] == 'semodule':
            stdout = [
                'libsemanage.semanage_direct_remove_key: Removing last dummy module '
                + '(no other dummy module exists at another priority).'
            ]
            for idx, value in enumerate(self.args):
                if value == "-r":
                    self.removed_modules.add(self.args[idx + 1])
        else:
            self.non_semodule_calls += 1

        return {'stdout': stdout}


def test_remove_custom_modules(monkeypatch):
    mock_modules = {'a': 99, 'b': 300, 'c': 400, 'abrt': 190}
    mock_templates = {'base_container': 400, 'net_container': 300}

    def consume_SELinuxModules_mocked(*models):

        semodule_list = [SELinuxModule(name=name, priority=priority, content='', removed=[])
                         for name, priority in mock_modules.items()]
        template_list = [SELinuxModule(name=name, priority=priority, content='', removed=[])
                         for name, priority in mock_templates.items()]
        yield SELinuxModules(modules=semodule_list, templates=template_list)

    monkeypatch.setattr(api, 'consume', consume_SELinuxModules_mocked)
    monkeypatch.setattr(selinuxprepare, 'run', run_mocked())

    selinuxprepare.remove_custom_modules()
    # 1 call for udica templates and 1 for other custom modules
    assert selinuxprepare.run.called == 2
    assert selinuxprepare.run.non_semodule_calls == 0
    # verify that remove_custom_modules tried to remove all given modules
    assert (set(mock_modules).union(set(mock_templates)) - selinuxprepare.run.removed_modules) == set()
