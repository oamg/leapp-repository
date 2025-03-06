from leapp.actors import Actor
from leapp.configs.actor import livemode as livemode_config_lib
from leapp.libraries.actor import scan_livemode_config as scan_livemode_config_lib
from leapp.models import InstalledRPM, LiveModeConfig
from leapp.tags import ExperimentalTag, FactsPhaseTag, IPUWorkflowTag


class LiveModeConfigScanner(Actor):
    """
    Read livemode configuration located at /etc/leapp/files/devel-livemode.ini
    """

    name = 'live_mode_config_scanner'
    config_schemas = livemode_config_lib.livemode_cfg_fields
    consumes = (InstalledRPM,)
    produces = (LiveModeConfig,)
    tags = (ExperimentalTag, FactsPhaseTag, IPUWorkflowTag,)

    def process(self):
        scan_livemode_config_lib.scan_config_and_emit_message()
