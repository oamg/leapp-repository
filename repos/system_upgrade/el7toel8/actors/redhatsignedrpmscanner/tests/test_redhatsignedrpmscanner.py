import mock

from leapp.libraries.common import rpms
from leapp.models import fields, InstalledRPM, InstalledRedHatSignedRPM, InstalledUnsignedRPM, Model, RPM
from leapp.snactor.fixture import current_actor_context


RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


class MockModel(Model):
    topic = RPM.topic
    list_field = fields.List(fields.Integer(), default=[42])
    list_field_nullable = fields.Nullable(fields.List(fields.String()))
    int_field = fields.Integer(default=42)


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRedHatSignedRPM)


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
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 5
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 4


def test_gpg_pubkey_pkg(current_actor_context):
    installed_rpm = [
        RPM(name='gpg-pubkey', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID aa17105e03152d37'),
        RPM(name='gpg-pubkey', version='0.1', release='1.sm01', epoch='1', packager='Tester', arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 9ea903b1361e896b'),
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 1
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 1


def test_create_lookup():
    # NOTE(ivasilev) Ideally should be tested separately from the actor, but since library
    # testing functionality is not yet implemented in leapp-repository the tests will reside here.
    model = MockModel()
    # plain non-empty list
    model.list_field.extend([-42])
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        # monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_message_mocked)
        lookup = rpms.create_lookup(MockModel, 'list_field', 'real')
        assert {42, -42} == lookup
    # empty list
    model.list_field = []
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field', 'real')
        assert {} == lookup
    # nullable list without default
    assert model.list_field_nullable is None
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field_nullable', 'real')
        assert {} == lookup
    # improper usage: lookup from non iterable field
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'int_field', 'real')
        assert {} == lookup
    # improper usage: lookup from iterable but bad attribute
    with mock.patch('leapp.libraries.stdlib.api.consume', return_value=(model,)):
        lookup = rpms.create_lookup(MockModel, 'list_field', 'nosuchattr')
        assert {} == lookup


def test_has_package(current_actor_context):
    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run()
    assert rpms.has_package(InstalledRedHatSignedRPM, 'sample01', context=current_actor_context)
    assert not rpms.has_package(InstalledRedHatSignedRPM, 'nosuchpackage', context=current_actor_context)
    assert rpms.has_package(InstalledUnsignedRPM, 'sample02', context=current_actor_context)
    assert not rpms.has_package(InstalledUnsignedRPM, 'nosuchpackage', context=current_actor_context)
