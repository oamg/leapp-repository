from leapp.actors import Actor
from leapp.libraries.actor import tcpwrappersconfigread
from leapp.models import TcpWrappersFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class TcpWrappersConfigRead(Actor):
    '''
    Parse tcp_wrappers configuration files /etc/hosts.{allow,deny}.
    '''

    name = 'tcp_wrappers_config_read'
    consumes = ()
    produces = (TcpWrappersFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(tcpwrappersconfigread.get_tcp_wrappers_facts())
