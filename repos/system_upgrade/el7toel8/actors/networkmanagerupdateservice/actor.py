import os
from subprocess import CalledProcessError

from leapp.actors import Actor
from leapp.libraries.stdlib import call
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class NetworkManagerUpdateService(Actor):
    name = 'network_manager_update_service'
    description = """
        This actor updates NetworkManager services status. On RHEL7 if
        the NetworkManager service was disabled and
        NetworkManager-wait-online enabled, the former would not be
        started. This changed on RHEL8, where NM-w-o 'Requires' NM and
        so NM can be started even if disabled. Upon upgrade, to keep
        the previous behavior we must disable NM-w-o when NM is
        disabled. See also:
        https://bugzilla.redhat.com/show_bug.cgi?id=1520865
    """
    consumes = ()
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        nm_enabled = self.unit_enabled('NetworkManager.service')
        nmwo_enabled = self.unit_enabled('NetworkManager-wait-online.service')
        self.log_services_state('initial', nm_enabled, nmwo_enabled)

        if not nm_enabled and nmwo_enabled:
            self.log.info('Disabling NetworkManager-wait-online.service')

            try:
                call(['systemctl', 'disable', 'NetworkManager-wait-online.service'])
            except (OSError, CalledProcessError) as e:
                self.log.warning('Error disabling NetworkManager-wait-online.service: {}'.format(e))
                return

            nm_enabled = self.unit_enabled('NetworkManager.service')
            nmwo_enabled = self.unit_enabled('NetworkManager-wait-online.service')
            self.log_services_state('after upgrade', nm_enabled, nmwo_enabled)

    def log_services_state(self, detail, nm, nmwo):
        self.log.info('Services state ({}):'.format(detail))
        self.log.info(' - NetworkManager            : {}'.format('enabled' if nm else 'disabled'))
        self.log.info(' - NetworkManager-wait-online: {}'.format('enabled' if nmwo else 'disabled'))

    def unit_enabled(self, name):
        try:
            ret = call(['systemctl', 'is-enabled', name])
            if len(ret) > 0:
                enabled = ret[0] == 'enabled'
            else:
                enabled = False
        except (OSError, CalledProcessError):
            enabled = False
        return enabled
