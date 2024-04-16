import os

import pytest

from leapp.libraries.stdlib import api
from leapp.models import LsblkEntry, LuksDumps, StorageInfo
from leapp.snactor.fixture import current_actor_context

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

TOKENS_ASSERT = {
        0: {
            "keyslot": 1,
            "token_type": "clevis-tpm2"
        },
        1: {
            "keyslot": 2,
            "token_type": "clevis-tang"
        },
        2: {
            "keyslot": 3,
            "token_type": "systemd-tpm2"
        },
}

CLEVIS_KEYSLOTS = {
    1: 'tpm2 \'{"hash":"sha256","key":"rsa","pcr_bank":"sha256","pcr_ids":"0,1,7"}\'',
    2: 'tang \'{"url":"http://localhost"}\''
}


class MockedRun(object):
    """Simple mock class for leapp.libraries.stdlib.run."""

    def __init__(self, variant, clevis_keyslots):
        """if exc_type provided, then it will be raised on
        instance call.

        :type exc_type: None or BaseException
        """
        self.logger = api.current_logger()

        self.commands = []
        self.variant = variant
        self.clevis_keyslots = clevis_keyslots

    def __call__(self, cmd, *args, **kwargs):
        self.commands.append(cmd)

        if len(cmd) == 3 and cmd[:2] == ['cryptsetup', 'luksDump']:
            dev_path = cmd[2]

            # We cannot have the output in a list, since the command is called per device. Therefore, we have to map
            # each device path to its output.
            output_files_per_device = {
                '/dev/nvme0n1p3': 'luksDump_nvme0n1p3{}.txt'.format(("_" + self.variant) if self.variant else "")
            }

            if dev_path not in output_files_per_device:
                raise ValueError(
                        'Attempting to call "cryptsetup luksDump" on an unexpected device: {}'.format(dev_path)
                )
            with open(os.path.join(CUR_DIR, 'files/{}'.format(output_files_per_device[dev_path]))) as f:
                return {"stdout": f.read()}
        elif len(cmd) >= 3 and cmd[:3] == ['clevis', 'luks', 'list']:
            dev_path = None
            keyslot = None

            device_flag = False
            keyslot_flag = False
            for element in cmd:
                if device_flag:
                    dev_path = element
                elif keyslot_flag:
                    keyslot = element

                device_flag = element == "-d"
                keyslot_flag = element == "-s"

            if dev_path is None or keyslot is None:
                raise ValueError('Attempting to call "clevis luks list" without specifying keyslot or device')
            if dev_path is None or keyslot is None or dev_path != "/dev/nvme0n1p3":
                raise ValueError('Attempting to call "clevis luks list" on invalid device')

            keyslot = int(keyslot)

            if keyslot in self.clevis_keyslots:
                return {"stdout": "{}: {}".format(keyslot, self.clevis_keyslots[keyslot])}

        return {}


@pytest.mark.parametrize(
    ("variant", "luks_version", "uuid", "tokens_assert"),
    [
        ('luks1', 1, '90242257-d00a-4019-aba6-03083f89404b', {}),
        ('luks2', 2, 'dfd8db30-2b65-4be9-8cae-65f5fac4a06f', {}),
        ('luks2_tokens', 2, '6b929b85-b01e-4aa3-8ad2-a05decae6e3d', TOKENS_ASSERT),
    ]
)
def test_actor_with_luks(monkeypatch, current_actor_context, variant, luks_version, uuid, tokens_assert):
    mocked_run = MockedRun(variant, CLEVIS_KEYSLOTS)
    monkeypatch.setattr('leapp.libraries.stdlib.run', mocked_run)

    with_luks = [
        LsblkEntry(
            name='/dev/nvme0n1', kname='/dev/nvme0n1', maj_min='259:0', rm='0', size='10G', bsize=10*(1 << 39),
            ro='0', tp='disk', parent_name='', parent_path='', mountpoint=''
        ),
        LsblkEntry(
            name='/dev/nvme0n1p3', kname='/dev/nvme0n1p3', maj_min='259:3', rm='0', size='10G', bsize=10*(1 << 39),
            ro='0', tp='part', parent_name='nvme0n1', parent_path='/dev/nvme0n1', mountpoint=''
        ),
        LsblkEntry(
            name='/dev/mapper/tst1', kname='/dev/dm-0', maj_min='253:0', rm='0', size='9G', bsize=9*(1 << 39), ro='0',
            tp='crypt', parent_name='nvme0n1p3', parent_path='/dev/nvme0n1p3', mountpoint=''
        ),
        # PKNAME is not set, so this crypt device will be ignored
        LsblkEntry(
            name='/dev/mapper/tst2', kname='/dev/dm-1', maj_min='253:0', rm='0', size='9G', bsize=9*(1 << 39), ro='0',
            tp='crypt', parent_name='', parent_path='', mountpoint=''
        )
    ]

    current_actor_context.feed(StorageInfo(lsblk=with_luks))
    current_actor_context.run()

    luks_dumps = current_actor_context.consume(LuksDumps)
    assert len(luks_dumps) == 1
    assert len(luks_dumps[0].dumps) == 1
    luks_dump = luks_dumps[0].dumps[0]

    assert luks_dump.version == luks_version
    assert luks_dump.uuid == uuid
    assert luks_dump.device_name == "nvme0n1p3"
    assert luks_dump.device_path == "/dev/nvme0n1p3"
    assert len(luks_dump.tokens) == len(tokens_assert)

    for token in luks_dump.tokens:
        assert token.token_id in tokens_assert
        assert token.keyslot == tokens_assert[token.token_id]["keyslot"]
        assert token.token_type == tokens_assert[token.token_id]["token_type"]
