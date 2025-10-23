import mock

from leapp.libraries.common import rpms
from leapp.libraries.common.config import mock_configs
from leapp.models import (
    DistributionSignedRPM,
    Distro,
    fields,
    InstalledRPM,
    InstalledUnsignedRPM,
    IPUConfig,
    Model,
    OSRelease,
    RPM,
    ThirdPartyRPM
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
    assert current_actor_context.consume(DistributionSignedRPM)
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert current_actor_context.consume(ThirdPartyRPM)


def test_actor_execution_with_signed_and_third_party_pkgs(current_actor_context):
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
    assert current_actor_context.consume(DistributionSignedRPM)
    assert len(current_actor_context.consume(DistributionSignedRPM)[0].items) == 5
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 4
    assert current_actor_context.consume(ThirdPartyRPM)
    assert len(current_actor_context.consume(ThirdPartyRPM)[0].items) == 4


def test_actor_execution_with_signed_and_third_party_pkgs_centos(current_actor_context):
    CENTOS_PACKAGER = 'CentOS BuildSystem <http://bugs.centos.org>'
    config = mock_configs.CONFIG

    config.os_release = OSRelease(
        release_id='centos',
        name='CentOS Linux',
        pretty_name='CentOS Linux 7 (Core)',
        version='7 (Core)',
        version_id='7'
    )
    config.distro = Distro(source='centos', target='centos')

    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 24c6a8a7f4a80eb5'),
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample03', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 05b555b38483c65d'),
        RPM(name='sample04', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample05', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 4eb84e71f2ee9d55'),
        RPM(name='sample06', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample07', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID fd372689897da07a'),
        RPM(name='sample08', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample09', version='0.1', release='1.sm01', epoch='1', packager=CENTOS_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 45689c882fa658e0')]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run(config_model=config)
    assert current_actor_context.consume(DistributionSignedRPM)
    assert len(current_actor_context.consume(DistributionSignedRPM)[0].items) == 3
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 6
    assert current_actor_context.consume(ThirdPartyRPM)
    assert len(current_actor_context.consume(ThirdPartyRPM)[0].items) == 6


def test_actor_execution_with_signed_unsigned_data_almalinux(current_actor_context):
    ALMALINUX_PACKAGER = 'AlmaLinux Packaging Team <packager@almalinux.org>'
    config = mock_configs.CONFIG

    config.os_release = OSRelease(
        release_id='almalinux',
        name='AlmaLinux',
        pretty_name='AlmaLinux 8.10 (Cerulean Leopard)',
        version='8.10 (Cerulean Leopard)',
        version_id='8.10'
    )
    config.distro = Distro(source='almalinux', target='almalinux')

    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', packager=ALMALINUX_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 2ae81e8aced7258b'),
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=ALMALINUX_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample03', version='0.1', release='1.sm01', epoch='1', packager=ALMALINUX_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 51d6647ec21ad6ea'),
        RPM(name='sample04', version='0.1', release='1.sm01', epoch='1', packager=ALMALINUX_PACKAGER, arch='noarch',
            pgpsig='SOME_OTHER_SIG_X'),
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run(config_model=config)
    assert current_actor_context.consume(DistributionSignedRPM)
    assert len(current_actor_context.consume(DistributionSignedRPM)[0].items) == 2
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 2


def test_actor_execution_with_unknown_distro(current_actor_context):
    config = mock_configs.CONFIG

    config.os_release = OSRelease(
        release_id='myos',
        name='MyOS Linux',
        pretty_name='MyOS Linux 7 (Core)',
        version='7 (Core)',
        version_id='7'
    )
    config.distro = Distro(source='myos', target='myos')

    current_actor_context.feed(InstalledRPM(items=[]))
    current_actor_context.run(config_model=config)
    assert not current_actor_context.consume(DistributionSignedRPM)
    assert not current_actor_context.consume(InstalledUnsignedRPM)
    assert not current_actor_context.consume(ThirdPartyRPM)


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
    assert current_actor_context.consume(DistributionSignedRPM)
    assert len(current_actor_context.consume(DistributionSignedRPM)[0].items) == 4
    assert not current_actor_context.consume(InstalledUnsignedRPM)[0].items
    assert not current_actor_context.consume(ThirdPartyRPM)[0].items


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
    assert current_actor_context.consume(DistributionSignedRPM)
    assert len(current_actor_context.consume(DistributionSignedRPM)[0].items) == 1
    assert not current_actor_context.consume(InstalledUnsignedRPM)[0].items
    assert not current_actor_context.consume(ThirdPartyRPM)[0].items


def test_gpg_pubkey_pkg(current_actor_context):
    installed_rpm = [
        RPM(name='gpg-pubkey', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID aa17105e03152d37'),
        RPM(name='gpg-pubkey', version='0.1', release='1.sm01', epoch='1', packager='Tester', arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 9ea903b1361e896b'),
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(DistributionSignedRPM)
    assert len(current_actor_context.consume(DistributionSignedRPM)[0].items) == 2
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert not current_actor_context.consume(InstalledUnsignedRPM)[0].items
    assert current_actor_context.consume(ThirdPartyRPM)
    assert not current_actor_context.consume(ThirdPartyRPM)[0].items


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
    assert rpms.has_package(DistributionSignedRPM, 'sample01', context=current_actor_context)
    assert not rpms.has_package(DistributionSignedRPM, 'nosuchpackage', context=current_actor_context)
    assert rpms.has_package(InstalledUnsignedRPM, 'sample02', context=current_actor_context)
    assert not rpms.has_package(InstalledUnsignedRPM, 'nosuchpackage', context=current_actor_context)
    assert rpms.has_package(ThirdPartyRPM, 'sample02', context=current_actor_context)
    assert not rpms.has_package(ThirdPartyRPM, 'nosuchpackage', context=current_actor_context)
