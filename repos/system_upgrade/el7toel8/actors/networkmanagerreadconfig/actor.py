from leapp.libraries.actor.networkmanagerreadconfig import read_nm_config, parse_nm_config, check_nm_dhcp
from leapp.actors import Actor
from leapp.models import NetworkManagerConfig
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class NetworkManagerReadConfig(Actor):
    """
    Provides data about NetworkManager configuration.

    After collecting data from NetworkManager tool, a message with relevant data will be produced.
    """

    name = 'network_manager_read_config'
    consumes = ()
    produces = (NetworkManagerConfig,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        nm_config = NetworkManagerConfig()

        cfg = read_nm_config()
        parser = parse_nm_config(cfg)

        if parser:
            check_nm_dhcp(nm_cfg=nm_config, parser=parser)

            self.produce(nm_config)
