import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import CryptoPolicyInfo

CRYPTO_CURRENT_STATE_FILE = '/etc/crypto-policies/state/current'


def process():
    if not os.path.exists(CRYPTO_CURRENT_STATE_FILE):
        # NOTE(pstodulk) just seatbelt, I do not expect the file is not present
        # skipping tests
        raise StopActorExecutionError(
                'File not found: {}'.format(CRYPTO_CURRENT_STATE_FILE),
                details={'details:': 'Cannot check the current set crypto policies.'}
        )
    with open(CRYPTO_CURRENT_STATE_FILE) as fp:
        api.produce(CryptoPolicyInfo(current_policy=fp.read().strip()))
