import pytest

from leapp.models import InstalledRedHatSignedRPM, RPM
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context


rpms = [
    (
        RPM(name='vim-minimal', version='1', release='1.el7',
            epoch='0', packager='foo', arch='x84_64',
            pgpsig='bar'),
        RPM(name='vim-enhanced', version='1', release='1.el7',
            epoch='0', packager='foo', arch='x84_64',
            pgpsig='bar')
    ),
    (
        RPM(name='vim-minimal', version='1', release='1.el7',
            epoch='0', packager='foo', arch='x84_64',
            pgpsig='bar'),
        RPM(name='ble', version='1', release='1.el7',
            epoch='0', packager='foo', arch='x84_64',
            pgpsig='bar')
    ),
    (
        RPM(name='vim-enhanced', version='1', release='1.el7',
            epoch='0', packager='foo', arch='x84_64',
            pgpsig='bar'),
        RPM(name='moo', version='1', release='1.el7',
            epoch='0', packager='foo', arch='x84_64',
            pgpsig='bar')
    ),
    (
        RPM(name='you', version='1', release='1.el7',
            epoch='0', packager='foo', arch='x84_64',
            pgpsig='bar'),
        RPM(name='hele', version='1', release='1.el7',
            epoch='0', packager='foo', arch='x84_64',
            pgpsig='bar')
    )
]


@pytest.mark.parametrize("rpms", rpms)
def test_actor_noerror(current_actor_context, rpms):
    facts = InstalledRedHatSignedRPM(items=rpms)

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    assert not reports
