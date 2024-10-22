from leapp.models import FirewalldDirectConfig

try:
    from firewall.core.fw import Firewall
except ImportError:
    pass


def read_config():
    try:
        fw = Firewall(offline=True)
    except NameError:
        # import failure missing means firewalld is not installed. Just return
        # the defaults.
        return FirewalldDirectConfig()

    # This does not actually start firewalld. It just loads the configuration a
    # la firewall-offline-cmd.
    fw.start()

    conf = fw.config.get_direct().export_config()

    conf_dict = {}
    conf_dict['has_permanent_configuration'] = any(conf)

    return FirewalldDirectConfig(**conf_dict)
