import json
import os

import pytest

from leapp.libraries.actor import persistentnetnamesconfig
from leapp.libraries.common.config import mock_configs
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.models import (
    InitrdIncludes,
    Interface,
    PCIAddress,
    PersistentNetNamesFacts,
    PersistentNetNamesFactsInitramfs,
    RenamedInterfaces,
    TargetInitramfsTasks
)

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
CUR_DIR = ""


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(TEST_DIR)
    yield
    os.chdir(previous_cwd)


def generate_link_file_mocked(interface):
    return '/etc/systemd/network/10-leapp-{}.link'.format(interface.name)


def interface_mocked(i=0):
    return Interface(
        name='n{}'.format(i),
        devpath='dp{}'.format(i),
        driver='d{}'.format(i),
        vendor='v{}'.format(i),
        pci_info=PCIAddress(
            domain='pd{}'.format(i),
            bus='pb{}'.format(i),
            function='pf{}'.format(i),
            device='pd{}'.format(i)
        ),
        mac='m{}'.format(i)
    )


def generate_interfaces(count):
    return [interface_mocked(i) for i in range(count)]


def test_identical(current_actor_context):
    interfaces = generate_interfaces(4)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    t_initrafms_tasks = current_actor_context.consume(TargetInitramfsTasks)[0]
    assert initrd_files.files == t_initrafms_tasks.include_files
    assert not renamed_interfaces.renamed
    assert not t_initrafms_tasks.include_files


def test_renamed_single_noneth(monkeypatch, current_actor_context):
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    interfaces[0].name = 'n4'
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    t_initrafms_tasks = current_actor_context.consume(TargetInitramfsTasks)[0]
    assert initrd_files.files == t_initrafms_tasks.include_files
    assert not renamed_interfaces.renamed
    assert len(t_initrafms_tasks.include_files) == 1
    assert '/etc/systemd/network/10-leapp-n0.link' in t_initrafms_tasks.include_files


def test_renamed_swap_noneth(monkeypatch, current_actor_context):
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    interfaces[0].name = 'n3'
    interfaces[3].name = 'n0'
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    t_initrafms_tasks = current_actor_context.consume(TargetInitramfsTasks)[0]
    assert initrd_files.files == t_initrafms_tasks.include_files
    assert not renamed_interfaces.renamed
    assert len(t_initrafms_tasks.include_files) == 2
    assert '/etc/systemd/network/10-leapp-n0.link' in t_initrafms_tasks.include_files
    assert '/etc/systemd/network/10-leapp-n3.link' in t_initrafms_tasks.include_files


def test_renamed_single_eth(monkeypatch, current_actor_context):
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    for i in range(4):
        interfaces[i].name = 'eth{}'.format(i)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    interfaces[0].name = 'eth4'
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    t_initrafms_tasks = current_actor_context.consume(TargetInitramfsTasks)[0]
    assert initrd_files.files == t_initrafms_tasks.include_files
    assert len(renamed_interfaces.renamed) == 1
    assert renamed_interfaces.renamed[0].rhel7_name == 'eth0'
    assert renamed_interfaces.renamed[0].rhel8_name == 'eth4'
    assert not t_initrafms_tasks.include_files


def test_renamed_swap_eth(monkeypatch, current_actor_context):
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    for i in range(4):
        interfaces[i].name = 'eth{}'.format(i)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    interfaces[0].name = 'eth3'
    interfaces[3].name = 'eth0'
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    t_initrafms_tasks = current_actor_context.consume(TargetInitramfsTasks)[0]
    assert initrd_files.files == t_initrafms_tasks.include_files
    assert len(renamed_interfaces.renamed) == 2
    for interface in renamed_interfaces.renamed:
        if interface.rhel7_name == 'eth0':
            assert interface.rhel8_name == 'eth3'
        elif interface.rhel7_name == 'eth3':
            assert interface.rhel8_name == 'eth0'
    assert not t_initrafms_tasks.include_files


def test_bz_1899455_crash_iface(monkeypatch, adjust_cwd):
    """
    Cover situation when network device is discovered on the src sys but not
    inside the upgrade environment.

    This typically happens when the network device needs specific drivers which
    are not present inside the upgrade initramfs. Usually it points to a missing
    actors that should influence the upgrade initramfs in a way the drivers are
    installed. In this situation, only correct thing we can do in this actor
    is print warning / report that we couldn't located particular devices so
    we cannot handle interface names related to this devices.
    """
    with open(os.path.join(CUR_DIR, 'files/crashed_ifaces.json')) as fp:
        json_msgs = json.load(fp)
    msgs = [
        PersistentNetNamesFacts.create(json_msgs["PersistentNetNamesFacts"]),
        PersistentNetNamesFactsInitramfs.create(json_msgs["PersistentNetNamesFactsInitramfs"]),
    ]
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)
    monkeypatch.setattr(
        persistentnetnamesconfig.api,
        "current_actor",
        # without this the actor exits early
        CurrentActorMocked(msgs=msgs, envars={"LEAPP_DISABLE_NET_NAMING_SCHEMES": "1"}),
    )
    monkeypatch.setattr(persistentnetnamesconfig.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(persistentnetnamesconfig.api, 'produce', produce_mocked())
    persistentnetnamesconfig.process()

    for prod_models in [RenamedInterfaces, InitrdIncludes, TargetInitramfsTasks]:
        any(isinstance(i, prod_models) for i in persistentnetnamesconfig.api.produce.model_instances)
    assert any(['Some network devices' in x for x in persistentnetnamesconfig.api.current_logger.warnmsg])


def test_no_network_renaming(monkeypatch):
    """
    This should cover OAMG-4243.
    """
    # this mock should be needed, as this function should be called, but just
    # for a check..
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    for i in range(4):
        interfaces[i].name = 'myinterface{}'.format(i)
    msgs = [PersistentNetNamesFacts(interfaces=interfaces)]
    interfaces[0].name = 'changedinterfacename0'
    msgs.append(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    mocked_actor = CurrentActorMocked(
        msgs=msgs,
        envars={
            "LEAPP_DISABLE_NET_NAMING_SCHEMES": "1",
            "LEAPP_NO_NETWORK_RENAMING": "1",
        },
    )
    monkeypatch.setattr(persistentnetnamesconfig.api, 'current_actor', mocked_actor)
    monkeypatch.setattr(persistentnetnamesconfig.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(persistentnetnamesconfig.api, 'produce', produce_mocked())
    persistentnetnamesconfig.process()

    ilog = 'Skipping handling of possibly renamed network interfaces: leapp executed with LEAPP_NO_NETWORK_RENAMING=1'
    assert ilog in persistentnetnamesconfig.api.current_logger.infomsg
    assert not persistentnetnamesconfig.api.produce.called
