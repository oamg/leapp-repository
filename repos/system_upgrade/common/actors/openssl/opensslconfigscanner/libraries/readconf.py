import errno

from leapp.libraries.common.rpms import check_file_modification
from leapp.libraries.stdlib import api
from leapp.models import OpenSslConfig, OpenSslConfigBlock, OpenSslConfigPair

CONFIG = '/etc/pki/tls/openssl.cnf'


def strip_whitespace_and_comments(line):
    """
    Returns everything before the first hash sign after stripping leading and trailing whitespace
    """
    parts = line.split("#", 1)
    return parts[0].strip()


def parse_config(config):
    """
    Parse openssl.cnf configuration
    """
    ret = OpenSslConfig(blocks=[])

    block = None
    for line in config:
        line = strip_whitespace_and_comments(line)
        if not line:
            continue

        # match the block header
        if line[0] == "[" and line[-1] == "]":
            name = line[1:-1].strip()
            block = OpenSslConfigBlock(name=name, pairs=[])
            ret.blocks.append(block)
            continue

        # the rest values are key-value pairs separated with equal sign
        el = line.split('=', 1)
        if len(el) < 2:
            # The special options .include and .pragma can appear without the equal sign
            if el[0].startswith('.include '):
                key = ".include"
                value = el[0][8:].strip()
            # elif el.startswith('.pragma '):
                # we do not care about this option now
            else:
                continue
        else:
            key = el[0].strip()
            value = el[1].strip()

        if block:
            pair = OpenSslConfigPair(key=key, value=value)
            block.pairs.append(pair)
            continue

        if key == 'openssl_conf':
            ret.openssl_conf = value

    return ret


def produce_config(producer, config):
    """
    Produce a Leapp message with all interesting openssl configuration options.
    """

    producer(config)


def read_config():
    """
    Read the actual configuration file.
    """
    try:
        with open(CONFIG, 'r') as fd:
            return fd.readlines()
    except IOError as err:
        if err.errno != errno.ENOENT:
            error = 'Failed to read config: {}'.format(str(err))
            api.current_logger().error(error)
        return []


def scan_config(producer):
    """
    Parse openssl.cnf file to create OpenSslConfig message.
    """

    # direct access to configuration file
    output = read_config()
    config = parse_config(output)

    # find out whether the file was modified from the one shipped in rpm
    config.modified = check_file_modification(CONFIG)

    produce_config(producer, config)
