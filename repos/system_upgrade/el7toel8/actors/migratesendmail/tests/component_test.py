import os

from six import text_type

from leapp.models import SendmailMigrationDecision
from leapp.reporting import Report


def test_actor_migration(tmpdir, current_actor_context):
    test_cfg_file = text_type(tmpdir.join('sendmail.cf'))
    with open(test_cfg_file, 'w') as file_out:
        file_out.write("IPv6:::1")
    current_actor_context.feed(SendmailMigrationDecision(migrate_files=[test_cfg_file]))
    current_actor_context.run()
    with open(test_cfg_file, 'r') as file_in:
        data = file_in.read()
    assert data == 'IPv6:0:0:0:0:0:0:0:1'
