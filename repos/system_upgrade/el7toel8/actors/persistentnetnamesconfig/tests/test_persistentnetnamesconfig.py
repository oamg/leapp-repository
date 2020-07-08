from leapp.libraries.actor import persistentnetnamesconfig
from leapp.models import PersistentNetNamesFacts, PersistentNetNamesFactsInitramfs
from leapp.models import RenamedInterface, RenamedInterfaces, InitrdIncludes
from leapp.models import Interface, PCIAddress


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
    current_actor_context.run()

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    assert not renamed_interfaces.renamed
    assert not initrd_files.files


def test_renamed_single_noneth(monkeypatch, current_actor_context):
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    interfaces[0].name = 'n4'
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run()

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    assert not renamed_interfaces.renamed
    assert len(initrd_files.files) == 1
    assert '/etc/systemd/network/10-leapp-n0.link' in initrd_files.files


def test_renamed_swap_noneth(monkeypatch, current_actor_context):
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    interfaces[0].name = 'n3'
    interfaces[3].name = 'n0'
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run()

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    assert not renamed_interfaces.renamed
    assert len(initrd_files.files) == 2
    assert '/etc/systemd/network/10-leapp-n0.link' in initrd_files.files
    assert '/etc/systemd/network/10-leapp-n3.link' in initrd_files.files


def test_renamed_single_eth(monkeypatch, current_actor_context):
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    for i in range(4):
        interfaces[i].name = 'eth{}'.format(i)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    interfaces[0].name = 'eth4'
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run()

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    assert len(renamed_interfaces.renamed) == 1
    assert renamed_interfaces.renamed[0].rhel7_name == 'eth0'
    assert renamed_interfaces.renamed[0].rhel8_name == 'eth4'
    assert not initrd_files.files


def test_renamed_swap_eth(monkeypatch, current_actor_context):
    monkeypatch.setattr(persistentnetnamesconfig, 'generate_link_file', generate_link_file_mocked)

    interfaces = generate_interfaces(4)
    for i in range(4):
        interfaces[i].name = 'eth{}'.format(i)
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interfaces))
    interfaces[0].name = 'eth3'
    interfaces[3].name = 'eth0'
    current_actor_context.feed(PersistentNetNamesFactsInitramfs(interfaces=interfaces))
    current_actor_context.run()

    renamed_interfaces = current_actor_context.consume(RenamedInterfaces)[0]
    initrd_files = current_actor_context.consume(InitrdIncludes)[0]
    assert len(renamed_interfaces.renamed) == 2
    for interface in renamed_interfaces.renamed:
        if interface.rhel7_name == 'eth0':
            assert interface.rhel8_name == 'eth3'
        elif interface.rhel7_name == 'eth3':
            assert interface.rhel8_name == 'eth0'
    assert not initrd_files.files
