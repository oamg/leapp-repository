import mock

from leapp.actors import Actor
from leapp.models import InstalledRPM, Report, RPM


def test_x32_x64(current_actor_context):
    problem_rpms = [
       RPM(name='brlapi', version='0.1', release='1.sm01', epoch='1', packager="RH_PACKAGER", arch='i686',
           pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
       RPM(name='gnome-online-accounts-devel', version='0.1', release='1.sm01', epoch='1',
           packager="RH_PACKAGER", arch='i686', pgpsig='SOME_OTHER_SIG_X'),
       RPM(name='geocode-glib-devel', version='0.1', release='1.sm01', epoch='1', packager="RH_PACKAGER",
           arch='i686', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 5326810137017186'),
       RPM(name='brlapi', version='0.1', release='1.sm01', epoch='1', packager="RH_PACKAGER", arch='x86_64',
           pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
       RPM(name='gnome-online-accounts-devel', version='0.1', release='1.sm01', epoch='1',
           packager="RH_PACKAGER", arch='x86_64', pgpsig='SOME_OTHER_SIG_X'),
       RPM(name='geocode-glib-devel', version='0.1', release='1.sm01', epoch='1', packager="RH_PACKAGER",
           arch='x86_64',
           pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 5326810137017186')
       ]

    current_actor_context.feed(InstalledRPM(items=problem_rpms))
    current_actor_context.run()
    report = current_actor_context.consume(Report)[0].report
    assert report['title'] == ('Some packages have both 32bit and 64bit version installed which are known to'
                               ' cause rpm transaction test to fail')
    assert {p['title'] for p in report['detail']['related_resources'] if p['scheme'] == 'package'} == \
           {'brlapi.i686', 'gnome-online-accounts-devel.i686', 'geocode-glib-devel.i686'}


def test_x64_only(current_actor_context):
    ok_rpms = [
       RPM(name='brlapi', version='0.1', release='1.sm01', epoch='1', packager="RH_PACKAGER", arch='x86_64',
           pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
       RPM(name='gnome-online-accounts-devel', version='0.1', release='1.sm01', epoch='1',
           packager="RH_PACKAGER", arch='x86_64', pgpsig='SOME_OTHER_SIG_X'),
       RPM(name='geocode-glib-devel', version='0.1', release='1.sm01', epoch='1', packager="RH_PACKAGER",
           arch='x86_64',
           pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 5326810137017186')
       ]

    current_actor_context.feed(InstalledRPM(items=ok_rpms))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_x32_only(current_actor_context):
    ok_rpms = [
       RPM(name='brlapi', version='0.1', release='1.sm01', epoch='1', packager="RH_PACKAGER", arch='i686',
           pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
       RPM(name='gnome-online-accounts-devel', version='0.1', release='1.sm01', epoch='1',
           packager="RH_PACKAGER", arch='i686', pgpsig='SOME_OTHER_SIG_X'),
       RPM(name='geocode-glib-devel', version='0.1', release='1.sm01', epoch='1', packager="RH_PACKAGER",
           arch='i686', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 5326810137017186'),
       ]

    current_actor_context.feed(InstalledRPM(items=ok_rpms))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
