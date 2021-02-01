import yaml

from leapp.libraries.stdlib import api

try:
    import dnf
except ImportError:
    api.current_logger().warning('modularity.py: failed to import dnf')


def get_modules():
    """
    Return info about all module streams as a list of dicts with their serialized YAML definitions.
    """
    base = dnf.Base()
    base.read_all_repos()
    base.fill_sack()

    module_base = dnf.module.module_base.ModuleBase(base)
    # this method is absent on RHEL 7, in which case there are no modules anyway
    if 'get_modules' not in dir(module_base):
        return []
    modules = module_base.get_modules('*')[0]
    return [yaml.load(module.getYaml()) for module in modules]
