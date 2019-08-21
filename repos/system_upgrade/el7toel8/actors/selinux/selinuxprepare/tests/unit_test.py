from leapp.libraries.stdlib import run, CalledProcessError
from leapp.libraries.actor import library
from leapp.libraries.stdlib import api
from leapp.models import SELinuxModules, SELinuxModule


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
            stdout = ["libsemanage.semanage_direct_remove_key: Removing last dummy module " +
                      "(no other dummy module exists at another priority)."]
            self.removed_modules.add(self.args[-1])
        else:
            self.non_semodule_calls += 1

        return {'stdout': stdout}


def test_remove_custom_modules(monkeypatch):
    mock_modules = {"a": 99,
                    "b": 300,
                    "c": 400,
                    "abrt": 190}

    def consume_SELinuxModules_mocked(*models):

        semodule_list = [SELinuxModule(name=k, priority=mock_modules[k], content="", removed=[])
                         for k in mock_modules]
        yield SELinuxModules(modules=semodule_list)

    monkeypatch.setattr(api, "consume", consume_SELinuxModules_mocked)
    monkeypatch.setattr(library, "run", run_mocked())

    library.remove_custom_modules()
    assert library.run.called == len(mock_modules)
    assert library.run.non_semodule_calls == 0
    # verify that remove_custom_modules tried to remove all given modules
    assert (set(mock_modules) - library.run.removed_modules) == set()
