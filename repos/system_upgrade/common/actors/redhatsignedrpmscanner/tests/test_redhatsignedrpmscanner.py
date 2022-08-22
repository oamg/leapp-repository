import mock

from leapp.libraries.common import rpms
from leapp.libraries.common.config import mock_configs
from leapp.models import (
    fields,
    InstalledRedHatSignedRPM,
    InstalledRPM,
    InstalledUnsignedRPM,
    IPUConfig,
    Model,
    RPM
)

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


class MockObject(Model):
    topic = RPM.topic
    value = fields.Integer(default=42)
    plan = fields.Nullable(fields.String())


class MockModel(Model):
    topic = RPM.topic
    list_field = fields.List(fields.Model(MockObject), default=[])
    list_field_nullable = fields.Nullable(fields.List(fields.String()))
    int_field = fields.Integer(default=42)


def test_no_installed_rpms(current_actor_context):
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert current_actor_context.consume(InstalledUnsignedRPM)


def test_actor_execution_with_signed_unsigned_data(current_actor_context):
    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample03', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 5326810137017186'),
        RPM(name='sample04', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample05', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 938a80caf21541eb'),
        RPM(name='sample06', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample07', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID fd372689897da07a'),
        RPM(name='sample08', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample09', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 45689c882fa658e0')]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 5
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 4


def test_all_rpms_signed(current_actor_context):
    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample03', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 5326810137017186'),
        RPM(name='sample04', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X')
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run(config_model=mock_configs.CONFIG_ALL_SIGNED)
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 4
    assert not current_actor_context.consume(InstalledUnsignedRPM)[0].items


def test_katello_pkg_goes_to_signed(current_actor_context):
    installed_rpm = [
        RPM(name='katello-ca-consumer-vm-098.example.com',
            version='1.0',
            release='1',
            epoch='0',
            packager='None',
            arch='noarch',
            pgpsig=''),
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run(config_model=mock_configs.CONFIG_ALL_SIGNED)
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 1
    assert not current_actor_context.consume(InstalledUnsignedRPM)[0].items


def test_gpg_pubkey_pkg(current_actor_context):
    installed_rpm = [
        RPM(name='gpg-pubkey', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID aa17105e03152d37'),
        RPM(name='gpg-pubkey', version='0.1', release='1.sm01', epoch='1', packager='Tester', arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 9ea903b1361e896b'),
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 1
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 1


def test_create_lookup():
    # NOTE(ivasilev) Ideally should be tested separately from the actor, but since library
    # testing functionality is not yet implemented in leapp-repository the tests will reside here.
    model = MockModel(list_field=[MockObject(value=42, plan="A"),
                                  MockObject(value=-42, plan="B"),
                                  MockObject(value=9999)])
    # plain non-empty list
    keys = ('value', )
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field', keys=keys)
        assert {(42, ), (-42, ), (9999, )} == lookup
    # plain list, multiple keys
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field', keys=('value', 'plan'))
        assert {(42, 'A'), (-42, 'B'), (9999, None)} == lookup
    # empty list
    model.list_field = []
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field', keys=keys)
        assert set() == lookup
    # nullable list without default
    assert model.list_field_nullable is None
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field_nullable', keys=keys)
        assert set() == lookup
    # improper usage: lookup from non iterable field
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'int_field', keys=keys)
        assert set() == lookup
    # improper usage: lookup from iterable but bad attribute
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field', keys=('nosuchattr',))
        assert set() == lookup
    # improper usage: lookup from iterable, multiple keys bad 1 bad
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field', keys=('value', 'nosuchattr'))
        assert set() == lookup


def test_has_package(current_actor_context):
    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert rpms.has_package(InstalledRedHatSignedRPM, 'sample01', context=current_actor_context)
    assert not rpms.has_package(InstalledRedHatSignedRPM, 'nosuchpackage', context=current_actor_context)
    assert rpms.has_package(InstalledUnsignedRPM, 'sample02', context=current_actor_context)
    assert not rpms.has_package(InstalledUnsignedRPM, 'nosuchpackage', context=current_actor_context)
