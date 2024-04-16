import functools

from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.actor.luksdump_parser import LuksDumpParser
from leapp.libraries.stdlib import api
from leapp.models import LuksDump, LuksDumps, LuksToken, StorageInfo


def aslist(f):
    """ Decorator used to convert generator to list """
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


def _get_clevis_type(device_path, keyslot):
    """
    Assuming the device is initialized using clevis, determine the type of
    clevis token associated to the specified keyslot.
    """
    try:
        result = stdlib.run(["clevis", "luks", "list", "-d", device_path, "-s", str(keyslot)])
    except OSError:
        message = ('A LUKS drive with clevis token was discovered, but there is '
                   'no clevis package installed. The clevis command is required '
                   'to determine clevis token type.')
        details = {'hint': 'Use dnf to install the "clevis-luks" package.'}
        raise StopActorExecutionError(message=message, details=details)
    except stdlib.CalledProcessError as e:
        api.current_logger().debug("clevis list command failed with an error code: {}".format(e.exit_code))

        message = ('The "clevis luks list" command failed. This'
                   'might be because the clevis-luks package is'
                   'missing on your system.')
        details = {'hint': 'Use dnf to install the "clevis-luks" package.'}
        raise StopActorExecutionError(message=message, details=details)

    line = result["stdout"].split()
    if len(line) != 3:
        raise StopActorExecutionError(
            'Invalid "clevis list" output detected'
        )

    return "clevis-{}".format(line[1])


@aslist
def _get_tokens(device_path, luksdump_dict):
    """ Given a parsed LUKS dump, produce a list of tokens """
    if "Version" not in luksdump_dict or luksdump_dict["Version"] != '2':
        return
    if "Tokens" not in luksdump_dict:
        raise StopActorExecutionError(
            'No tokens in cryptsetup luksDump output'
        )

    for token_id in luksdump_dict["Tokens"]:
        token = luksdump_dict["Tokens"][token_id]

        if "Keyslot" not in token or "type" not in token:
            raise StopActorExecutionError(
                'Token specification does not contain keyslot or type',
            )
        keyslot = int(token["Keyslot"])
        token_type = token["type"]

        if token_type == "clevis":
            token_type = _get_clevis_type(device_path, keyslot)

        yield LuksToken(
                token_id=int(token_id),
                keyslot=keyslot,
                token_type=token_type
        )


def get_luks_dump_by_device(device_path, device_name):
    """ Determine info about LUKS device using cryptsetup and clevis commands """

    try:
        result = stdlib.run(['cryptsetup', 'luksDump', device_path])
        luksdump_dict = LuksDumpParser.parse(result["stdout"].splitlines())

        version = int(luksdump_dict["Version"]) if "Version" in luksdump_dict else None
        uuid = luksdump_dict["UUID"] if "UUID" in luksdump_dict else None
        if version is None or uuid is None:
            api.current_logger().error(
                'Failed to detect UUID or version from the output "cryptsetup luksDump {}" command'.format(device_path)
            )
            raise StopActorExecutionError(
                'Failed to detect UUID or version from the output "cryptsetup luksDump {}" command'.format(device_path)
            )

        return LuksDump(
                version=version,
                uuid=uuid,
                device_path=device_path,
                device_name=device_name,
                tokens=_get_tokens(device_path, luksdump_dict)
        )

    except (OSError, stdlib.CalledProcessError) as ex:
        api.current_logger().error(
                'Failed to execute "cryptsetup luksDump" command: {}'.format(ex)
        )
        raise StopActorExecutionError(
            'Failed to execute "cryptsetup luksDump {}" command'.format(device_path),
            details={'details': str(ex)}
        )


@aslist
def get_luks_dumps():
    """ Collect info abaout every active LUKS device """

    for storage_info in api.consume(StorageInfo):
        for blk in storage_info.lsblk:
            if blk.tp == 'crypt' and blk.parent_path:
                yield get_luks_dump_by_device(blk.parent_path, blk.parent_name)


def get_luks_dumps_model():
    return LuksDumps(dumps=get_luks_dumps())
