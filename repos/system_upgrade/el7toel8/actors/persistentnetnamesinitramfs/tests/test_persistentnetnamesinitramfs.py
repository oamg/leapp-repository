import pytest

from leapp.libraries.common import persistentnetnames
from leapp.models import Interface, PCIAddress, PersistentNetNamesFactsInitramfs
from leapp.snactor.fixture import current_actor_context


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


class interfaces_mocked(object):
    def __init__(self, count):
        self.count = count

    def __call__(self):
        for i in range(self.count):
            yield interface_mocked(i)


@pytest.mark.parametrize('count', [0, 1, 8, 256])
def test_run(monkeypatch, current_actor_context, count):
    monkeypatch.setattr(persistentnetnames, 'interfaces', interfaces_mocked(count))
    current_actor_context.run()
    assert len(current_actor_context.consume(PersistentNetNamesFactsInitramfs)[0].interfaces) == count
