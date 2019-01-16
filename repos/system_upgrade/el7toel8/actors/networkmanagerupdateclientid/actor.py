from subprocess import CalledProcessError

from leapp.actors import Actor
from leapp.libraries.stdlib import call
from leapp.models import NetworkManagerConfig
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class NetworkManagerUpdateClientId(Actor):
    name = 'network_manager_update_client_id'
    description = """
       This actor updates DHCP client-ids when migrating to
       RHEL8. When using dhcp=dhclient on RHEL7, a non-hexadecimal
       client-id (a string) is sent on the wire as is (i.e. the first
       character is the 'type' as per RFC 2132 section 9.14). On
       RHEL8, a zero byte is prepended to string-only client-ids. To
       preserve behavior on upgrade, we convert client-ids to the
       hexadecimal form.
    """
    consumes = (NetworkManagerConfig,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        for nm_config in self.consume(NetworkManagerConfig):
            if nm_config.dhcp != '' and nm_config.dhcp != 'dhclient':
                self.log.info('DHCP client is {}, nothing to do'.format(nm_config.dhcp))
                return

            try:
                r = call(['nm-update-client-ids.py'])
            except (OSError, CalledProcessError) as e:
                self.log.warning('Error calling script: {}'.format(e))
                return

            self.log.info('Updated client-ids: {}'.format(r))


