import pytest

from leapp.libraries.actor import scancustommodifications
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api

FILES_FROM_RPM = """
repos/system_upgrade/el8toel9/actors/xorgdrvfact/libraries/xorgdriverlib.py
repos/system_upgrade/el8toel9/actors/anotheractor/actor.py
repos/system_upgrade/el8toel9/files
"""

FILES_ON_SYSTEM = """
repos/system_upgrade/el8toel9/actors/xorgdrvfact/libraries/xorgdriverlib.py
repos/system_upgrade/el8toel9/actors/anotheractor/actor.py
repos/system_upgrade/el8toel9/files
/some/unrelated/to/leapp/file
repos/system_upgrade/el8toel9/files/file/that/should/not/be/there
repos/system_upgrade/el8toel9/actors/actor/that/should/not/be/there
"""

VERIFIED_FILES = """
.......T.    repos/system_upgrade/el8toel9/actors/xorgdrvfact/libraries/xorgdriverlib.py
S.5....T.    repos/system_upgrade/el8toel9/actors/anotheractor/actor.py
S.5....T.  c etc/leapp/files/pes-events.json
"""


@pytest.mark.parametrize('a_file,name', [
    ('repos/system_upgrade/el8toel9/actors/checkblacklistca/actor.py', 'checkblacklistca'),
    ('repos/system_upgrade/el7toel8/actors/checkmemcached/actor.py', 'check_memcached'),
    # actor library
    ('repos/system_upgrade/el7toel8/actors/checkmemcached/libraries/checkmemcached.py', 'check_memcached'),
    # actor file
    ('repos/system_upgrade/common/actors/createresumeservice/files/leapp_resume.service', 'create_systemd_service'),
    ('repos/system_upgrade/common/actors/commonleappdracutmodules/files/dracut/85sys-upgrade-redhat/do-upgrade.sh',
     'common_leapp_dracut_modules'),
    # not a library and not an actor file
    ('repos/system_upgrade/el7toel8/models/authselect.py', ''),
    ('repos/system_upgrade/common/files/rhel_upgrade.py', ''),
    # common library not tied to any actor
    ('repos/system_upgrade/common/libraries/mounting.py', ''),
    ('repos/system_upgrade/common/libraries/config/version.py', ''),
    ('repos/system_upgrade/common/libraries/multipathutil.py', ''),
    ('repos/system_upgrade/common/libraries/config/version.py', ''),
    ('repos/system_upgrade/common/libraries/dnfplugin.py', ''),
    ('repos/system_upgrade/common/libraries/testutils.py', ''),
    # the rest of false positives discovered by dkubek
    ('repos/system_upgrade/common/actors/setuptargetrepos/libraries/setuptargetrepos_repomap.py', 'setuptargetrepos'),
    ('repos/system_upgrade/el8toel9/actors/sssdfacts/libraries/sssdfacts8to9.py', 'sssd_facts_8to9'),
    ('repos/system_upgrade/el8toel9/actors/nisscanner/libraries/nisscan.py', 'nis_scanner'),
    ('repos/system_upgrade/common/actors/setuptargetrepos/libraries/setuptargetrepos_repomap.py', 'setuptargetrepos'),
    ('repos/system_upgrade/common/actors/repositoriesmapping/libraries/repositoriesmapping.py', 'repository_mapping'),
    ('repos/system_upgrade/common/actors/peseventsscanner/libraries/peseventsscanner_repomap.py',
     'pes_events_scanner')
])
def test_deduce_actor_name_from_file(a_file, name):
    assert scancustommodifications.deduce_actor_name(a_file) == name


def mocked__run_command(list_of_args, log_message, checked=True):
    if list_of_args == ['rpm', '-ql', 'leapp-upgrade-el8toel9']:
        # get source of truth
        return FILES_FROM_RPM.strip().split('\n')
    if list_of_args and list_of_args[0] == 'find':
        # listing files in directory
        return FILES_ON_SYSTEM.strip().split('\n')
    if list_of_args == ['rpm', '-V', '--nomtime', 'leapp-upgrade-el8toel9']:
        # checking authenticity
        return VERIFIED_FILES.strip().split('\n')
    return []


def test_check_for_modifications(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='8.9', dst_ver='9.3'))
    monkeypatch.setattr(scancustommodifications, '_run_command', mocked__run_command)
    modifications = scancustommodifications.check_for_modifications('repository')
    modified = [m for m in modifications if m.type == 'modified']
    custom = [m for m in modifications if m.type == 'custom']
    configurations = [m for m in modifications if m.component == 'configuration']
    assert len(modified) == 3
    assert modified[0].filename == 'repos/system_upgrade/el8toel9/actors/xorgdrvfact/libraries/xorgdriverlib.py'
    assert modified[0].rpm_checks_str == '.......T.'
    assert len(custom) == 3
    assert custom[0].filename == '/some/unrelated/to/leapp/file'
    assert custom[0].rpm_checks_str == ''
    assert len(configurations) == 1
    assert configurations[0].filename == 'etc/leapp/files/pes-events.json'
    assert configurations[0].rpm_checks_str == 'S.5....T.'
