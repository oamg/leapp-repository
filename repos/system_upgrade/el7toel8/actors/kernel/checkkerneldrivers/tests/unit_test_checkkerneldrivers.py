import pytest

from leapp.models import ActiveKernelModule, ActiveKernelModulesFacts
from leapp.reporting import Report

kmodules_ok = [
    ActiveKernelModule(filename="i915", parameters=[]),
    ActiveKernelModule(filename="serial", parameters=[]),
    ActiveKernelModule(filename="pcieport", parameters=[]),
    ActiveKernelModule(filename="nvme", parameters=[]),
]

kmodules_removed = [
    ActiveKernelModule(filename="floppy", parameters=[]),
    ActiveKernelModule(filename="initio", parameters=[]),
    ActiveKernelModule(filename="pata_acpi", parameters=[]),
    ActiveKernelModule(filename="iwl4965", parameters=[]),
]


@pytest.mark.parametrize("kmodules,expected", [
    ([], True),
    (kmodules_ok, True),
    (kmodules_removed, False),
    (kmodules_removed + kmodules_ok, False),
])
def test_drivers(kmodules, expected, current_actor_context):
    """
    Tests CheckKernelDrivers actor by feeding it mocked PCI devices with their
    respective drivers, if they have one.  Actor should produce a report iff any
    mocked devices from kmodules_removed are fed to the actor, since their
    drivers are removed in RHEL8 (as per 'files/removed_drivers.txt').
    """
    current_actor_context.feed(ActiveKernelModulesFacts(kernel_modules=kmodules))
    current_actor_context.run()
    if expected:
        assert not current_actor_context.consume(Report)
    else:
        assert current_actor_context.consume(Report)
