import pytest

from leapp.models import InstalledRedHatSignedRPM, Report, RPM
from leapp.snactor.fixture import current_actor_context

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'

ballast1 = [
    RPM(name='b1', version='1', release='1', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s'),
    RPM(name='kernel', version='1', release='1', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s'),
    RPM(name='b2', version='1', release='1', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s')
]
ballast2 = [
    RPM(name='b3', version='1', release='1', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s'),
    RPM(name='kernel', version='1', release='1', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s'),
    RPM(name='b4', version='1', release='1', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s')
]
debug_kernels = [
    RPM(name='kernel-debug', version='3.10.0', release='957.27.4.el7',
        epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s'),
    RPM(name='kernel-debug', version='3.10.0', release='957.35.1.el7',
        epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s'),
    RPM(name='kernel-debug', version='3.10.0', release='957.43.1.el7',
        epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='s')
]


@pytest.mark.parametrize('n', [0, 1, 2, 3])
def test_process_debug_kernels(current_actor_context, n):
    current_actor_context.feed(InstalledRedHatSignedRPM(items=ballast1+debug_kernels[:n]+ballast2))
    current_actor_context.run()
    if n < 2:
        assert not current_actor_context.consume(Report)
    else:
        assert current_actor_context.consume(Report)
