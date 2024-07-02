import json
import os
import os.path

from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, LiveModeConfigFacts, ModelViolationError
from leapp.tags import ExperimentalTag, FactsPhaseTag, IPUWorkflowTag

LEAPP_LIVEMODE_JSON = '/etc/leapp/files/livemode.json'


class LiveModeConfig(Actor):
    """
    Read /etc/leapp/files/livemode.json
    """

    name = 'live_mode_config'
    consumes = (InstalledRPM)
    produces = (LiveModeConfigFacts)
    tags = (ExperimentalTag, FactsPhaseTag, IPUWorkflowTag,)

    def process(self):
        unsupported = os.getenv('LEAPP_UNSUPPORTED', 0)
        if unsupported != '1' or not os.path.exists(LEAPP_LIVEMODE_JSON):
            return

        api.current_logger().info(
           'Loading livemode config from {}'.format(LEAPP_LIVEMODE_JSON)
        )

        try:
            with open(LEAPP_LIVEMODE_JSON) as f:
                config = json.load(f)
        except ValueError as error:
            raise StopActorExecutionError(
                'Cannot parse live mode config',
                details={'Problem': str(error)})
        except OSError as error:
            api.current_logger().error('Failed to read livemode configuration. Error: %s', error)
            raise StopActorExecutionError(
                'Cannot read live mode config',
                details={'Problem': 'reading {} failed.'.format(LEAPP_LIVEMODE_JSON)})

        if api.current_actor().configuration.architecture != 'x86_64':
            raise StopActorExecutionError(
                'Cannot operate on this architecture.',
                details={'Problem': 'Live mode has been attempted on x86_64 only.'})

        if not has_package(InstalledRPM, 'squashfs-tools'):
            raise StopActorExecutionError(
                'Cannot use mksquashfs.',
                details={'Problem': 'The squashfs-tools package is mandatory for the live mode.'})

        try:
            api.produce(LiveModeConfigFacts(
                enabled=int(config['enabled']),
                url=config['url'],
                squashfs=config['squashfs'],
                with_cache=config['with_cache'],
                temp_dir=config['temp_dir'],
                dracut_network=config['dracut_network'],
                nm=config['nm'],
                packages=config['packages'],
                autostart=int(config['autostart']),
                authorized_keys=config['authorized_keys'],
                strace=config['strace'])
            )
        except ModelViolationError as error:
            raise StopActorExecutionError(
                'Cannot correctly parse {}'.format(LEAPP_LIVEMODE_JSON),
                details={'Problem': str(error)})
