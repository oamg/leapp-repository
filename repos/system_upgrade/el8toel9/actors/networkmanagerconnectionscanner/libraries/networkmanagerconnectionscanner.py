import errno
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import utils
from leapp.libraries.stdlib import api
from leapp.models import NetworkManagerConnection, NetworkManagerConnectionProperty, NetworkManagerConnectionSetting

libnm_available = False
err_details = None
try:
    import gi
    try:
        gi.require_version("NM", "1.0")
        from gi.repository import GLib, NM
        libnm_available = True
    except ValueError:
        err_details = 'NetworkManager-libnm package is not available'
except ImportError:
    err_details = 'python3-gobject-base package is not available'

NM_CONN_DIR = "/etc/NetworkManager/system-connections"


def process_file(filename):
    # We're running this through libnm in order to clear the secrets.
    # We don't know what keys are secret, but libnm does.
    keyfile = GLib.KeyFile()
    keyfile.load_from_file(filename, GLib.KeyFileFlags.NONE)
    con = NM.keyfile_read(keyfile, NM_CONN_DIR, NM.KeyfileHandlerFlags.NONE)
    con.clear_secrets()
    keyfile = NM.keyfile_write(con, NM.KeyfileHandlerFlags.NONE)
    cp = utils.parse_config(keyfile.to_data()[0])

    settings = []
    for setting_name in cp.sections():
        properties = []
        for name, value in cp.items(setting_name, raw=True):
            properties.append(NetworkManagerConnectionProperty(name=name, value=value))
        settings.append(
            NetworkManagerConnectionSetting(name=setting_name, properties=properties)
        )
    api.produce(NetworkManagerConnection(filename=filename, settings=settings))


def process_dir(directory):
    try:
        keyfiles = os.listdir(directory)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return
        raise

    for f in keyfiles:
        process_file(os.path.join(NM_CONN_DIR, f))


def process():
    if libnm_available:
        process_dir(NM_CONN_DIR)
    else:
        raise StopActorExecutionError(
            message='Failed to read NetworkManager connections',
            details=err_details
            )
