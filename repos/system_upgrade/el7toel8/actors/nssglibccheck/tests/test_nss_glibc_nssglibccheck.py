from leapp.snactor.fixture import current_actor_context
from leapp.libraries.actor import utils
from leapp import reporting
from leapp.libraries.common.testutils import create_report_mocked


TEST_DATA = '''
#     passwd: sss files wins # from profile
#     hosts: files dns  # from user file

passwd:     sss files systemd
group:      sss files systemd
netgroup:   sss files wins
automount:  sss files winbind
services:   sss files
foo:        sss files #winbind
'''


def test_blacklister(current_actor_context):
    caught = list(utils.check_modules(
        [l.strip() for l in TEST_DATA.splitlines()],
        ('wins', 'winbind',),
    ))

    assert len(caught) == 2

    assert caught[0].module == 'wins' and caught[0].lineno == 7
    assert caught[1].module == 'winbind' and caught[1].lineno == 8


def test_inhibition(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    utils.process_lines(
        [l.strip() for l in TEST_DATA.splitlines()],
        ('wins', 'winbind',),
        '/nss_path'
    )
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
