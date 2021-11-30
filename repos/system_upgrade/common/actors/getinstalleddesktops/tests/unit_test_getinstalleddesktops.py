from leapp.models import InstalledDesktopsFacts, InstalledRPM, RPM
from leapp.snactor.fixture import current_actor_context

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'
Gnome_RPM = RPM(name='gnome-session', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')
KDE_RPM = RPM(name='kde-workspace', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
              pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')


def test_Gnome_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[Gnome_RPM, ]))
    current_actor_context.run()
    message = current_actor_context.consume(InstalledDesktopsFacts)[0]
    assert message.gnome_installed


def test_KDE_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[KDE_RPM, ]))
    current_actor_context.run()
    message = current_actor_context.consume(InstalledDesktopsFacts)[0]
    assert message.kde_installed


def test_KDE_Gnome_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[Gnome_RPM, KDE_RPM]))
    current_actor_context.run()
    message = current_actor_context.consume(InstalledDesktopsFacts)[0]
    assert message.gnome_installed and message.kde_installed


def test_no_desktop_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[]))
    current_actor_context.run()
    message = current_actor_context.consume(InstalledDesktopsFacts)[0]
    assert not message.gnome_installed and not message.kde_installed
