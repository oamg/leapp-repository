from leapp.actors import Actor
from leapp.libraries.actor.networkmanagerreadconfig import check_nm_dhcp, parse_nm_config, read_nm_config
from leapp.models import NetworkManagerConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


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
