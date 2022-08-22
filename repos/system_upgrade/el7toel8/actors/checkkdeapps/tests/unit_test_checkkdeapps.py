from leapp.models import InstalledKdeAppsFacts, InstalledRPM, RPM
from leapp.snactor.fixture import current_actor_context

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'

#  KDE apps (only name matters, other values are irrelevant)
okular_RPM = RPM(name='okular', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                 pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')
kdenetwork_RPM = RPM(name='kdenetwork', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER,
                     arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')
kate_RPM = RPM(name='kate', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')

# Some other apps to check false detection (only name matters, other values are irrelevant)
epiphany_PRM = RPM(name='epiphany', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                   pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')
polari_RPM = RPM(name='polari', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                 pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')


def test_no_app_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[]))
    current_actor_context.run()
    message = current_actor_context.consume(InstalledKdeAppsFacts)[0]
    assert not message.installed_apps


def test_no_KDE_app_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[epiphany_PRM, polari_RPM]))
    current_actor_context.run()
    message = current_actor_context.consume(InstalledKdeAppsFacts)[0]
    assert not message.installed_apps


def test_only_KDE_apps_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[okular_RPM, kdenetwork_RPM, kate_RPM]))
    current_actor_context.run()
    message = current_actor_context.consume(InstalledKdeAppsFacts)[0]
    assert len(message.installed_apps) == 3


def test_many_apps_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[okular_RPM, kdenetwork_RPM, kate_RPM, epiphany_PRM, polari_RPM]))
    current_actor_context.run()
    message = current_actor_context.consume(InstalledKdeAppsFacts)[0]
    assert len(message.installed_apps) == 3
