import errno
from os import listdir, path

from leapp.libraries.stdlib import api
from leapp.models import IfCfg, IfCfgProperty

SYSCONFIG_DIR = "/etc/sysconfig/network-scripts"


def aux_file(prefix, filename):
    directory = path.dirname(filename)
    keys_base = path.basename(filename).replace("ifcfg-", prefix)
    return path.join(directory, keys_base)


def process_ifcfg(filename, secrets=False):
    if not path.exists(filename):
        return None

    properties = []
    for line in open(filename).readlines():
        try:
            (name, value) = line.split("#")[0].strip().split("=")
            if secrets:
                value = None
        except ValueError:
            # We're not interested in lines that are not
            # simple assignments. Play it safe.
            continue

        # Deal with simple quoting. We don't expand anything, nor do
        # multiline strings or anything of that sort.
        if value is not None and len(value) > 1 and value[0] == value[-1]:
            if value.startswith('"') or value.startswith("'"):
                value = value[1:-1]

        properties.append(IfCfgProperty(name=name, value=value))
    return properties


def process_plain(filename):
    if not path.exists(filename):
        return None
    return open(filename).readlines()


def process_file(filename):
    api.produce(IfCfg(
        filename=filename,
        properties=process_ifcfg(filename),
        secrets=process_ifcfg(aux_file("keys-", filename), secrets=True),
        rules=process_plain(aux_file("rule-", filename)),
        rules6=process_plain(aux_file("rule6-", filename)),
        routes=process_plain(aux_file("route-", filename)),
        routes6=process_plain(aux_file("route6-", filename)),
    ))


def process_dir(directory):
    try:
        keyfiles = listdir(directory)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return
        raise

    for f in keyfiles:
        if f.startswith("ifcfg-"):
            process_file(path.join(directory, f))


def process():
    process_dir(SYSCONFIG_DIR)
