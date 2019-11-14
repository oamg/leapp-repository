import os
import json

from leapp.actors import Actor
from leapp.models import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.utils.audit import get_connection
from leapp import reporting


class UnsupportedUpgradeCheck(Actor):
    """
    Checks enviroment variables and produces a warning report if the upgrade is unsupported.

    Upgrade is unsupported if any LEAPP_DEVEL_* variable is used or an experimental actor is enabled.
    This can be overridden by setting the variable LEAPP_UNSUPPORTED (at user's own risk).
    """

    name = 'unsupported_upgrade_check'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        env = os.environ
        devel_vars = {k: env[k] for k in env if k.startswith('LEAPP_DEVEL_')}
        override = 'LEAPP_UNSUPPORTED' in env

        if devel_vars and not override:
            reporting.create_report([
                reporting.Title('Upgrade inhibited due to usage of development variables'),
                reporting.Summary(
                    'One or more environment variables in the form of LEAPP_DEVEL_* have been detected.\n'
                    'These variables are for development purposes only and can interfere with the upgrade '
                    'process in unexpected ways. As such, a successful and safe upgrade process cannot be '
                    'guaranteed and the upgrade is unsupported.\n'
                    'Found development variables:\n- ' + '\n- '.join(devel_vars) + '\n'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Flags([reporting.Flags.INHIBITOR]),
                reporting.Tags([reporting.Tags.UPGRADE_PROCESS, reporting.Tags.SANITY]),
                reporting.Remediation(hint='Invoke leapp without any LEAPP_DEVEL_* environment variables.')
            ])

        experimental = []
        with get_connection(None) as db:
            conf = db.execute("SELECT configuration FROM execution "
                              "WHERE kind = 'upgrade' OR kind = 'preupgrade' "
                              "ORDER BY id DESC LIMIT 1").fetchone()
            if conf:
                experimental = json.loads(conf[0])["whitelist_experimental"]
        if experimental and not override:
            reporting.create_report([
                reporting.Title('Upgrade inhibited due to enabled experimental actors'),
                reporting.Summary(
                    'One or more enabled experimental actors have been detected.\n'
                    'These actors are unstable or in development and can interfere with the upgrade '
                    'process in unexpected ways. As such, a successful and safe upgrade process cannot be '
                    'guaranteed and the upgrade is unsupported.\n'
                    'Found enabled experimental actors:\n- ' + '\n- '.join(experimental) + '\n'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Flags([reporting.Flags.INHIBITOR]),
                reporting.Tags([reporting.Tags.UPGRADE_PROCESS, reporting.Tags.SANITY]),
                reporting.Remediation(hint='Invoke leapp without any --whitelist-experimental options.')
            ])
