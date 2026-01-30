from leapp.libraries.actor import enablephpmodule
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import EnabledModules, Module


def test_php82_enabled_on_source(monkeypatch):
    enabled_modules = EnabledModules(modules=[
        Module(name='php', stream='8.2'),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[enabled_modules]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    enablephpmodule.enable_php_module()

    produced = api.produce.model_instances[0]
    assert produced.modules_to_enable[0].name == 'php'
    assert produced.modules_to_enable[0].stream == '8.2'


def test_php82_not_enabled_on_source(monkeypatch):
    enabled_modules = EnabledModules(modules=[
        Module(name='php', stream='7.4'),
        Module(name='nodejs', stream='18'),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[enabled_modules]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    enablephpmodule.enable_php_module()

    assert api.produce.called == 0


def test_no_modules_enabled(monkeypatch):
    enabled_modules = EnabledModules(modules=[])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[enabled_modules]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    enablephpmodule.enable_php_module()

    assert api.produce.called == 0


def test_no_enabled_modules_message(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    enablephpmodule.enable_php_module()

    assert api.produce.called == 0
