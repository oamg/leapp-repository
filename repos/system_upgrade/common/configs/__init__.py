# This is code that needs to go in the leapp framework.
# Putting it here for now so that everything is in one git repo.
__metaclass__ = type


import abc
import importlib
import os
import pkgutil
import sys

import six
import yaml

try:
    # Compiled versions if available, for speed
    from yaml import CSafeLoader as SafeLoader, CSafeDumper as SafeDumper
except ImportError:
    from yaml import SafeLoader, SafeDumper


@six.add_metaclass(abc.ABCMeta)
class Config:
    @abc.abstractproperty
    def section():
        pass

    @abc.abstractproperty
    def name():
        pass

    @abc.abstractproperty
    def type_():
        pass

    @abc.abstractproperty
    def description():
        pass

    @classmethod
    def to_dict(cls):
        """
        Return a dictionary representation of the config item that would be suitable for putting
        into a config file.
        """
        representation = {
            cls.section: {
                '{0}_description__'.format(cls.name): cls.description
            }
        }
        ### TODO: Retrieve the default values from the type field.
        # representation[cls.section][cls.name] = cls.type_.get_default()

        return representation


def parse_system_config_files(config_dir='/etc/leapp/config.d'):
    """
    Read all configuration files from the config_dir and return a dict with their values.
    """
    potential_config_files = []
    for root, dirs, files in os.walk(config_dir):
        for file in files:
            potential_config_fiels.append(os.path.join(root, file))

    potential_config_files.sort()
    all_config = {}
    for filename in potential_config_files:
        try:
            cfg = SafeLoader(filename)
        except Exception as e:
            if filename.endswith('.yml') or filename.endswith('.yaml'):
                ### TODO: Should use a logger once we know where this will live
                print("Warning: unparsable yaml file {0} in the config directory."
                      " Error: {1}".format(filename, str(e)))
            continue

        ### TODO: Should we check whether we are overwriting any already defined keys?
        all_configs.extend(cfg)

    return all_config


def all_repository_config_schemas():
    """
    Return all the configuration items present in all repositories.
    """
    # Need to loop through all the configuration defined in all the
    # repositories and then return them.
    # POC Code
    config_path = "/srv/leapp/leapp-repository-git/actor-config/repos"
    config_mod_prefix = "system_upgrade.common.configs"
    configs = set()

    # In Python 3, this is a NamedTuple where m[1] == m.name and m[2] == m.ispkg
    modules = (m[1] for m in pkgutil.iter_modules(config_path, prefix=config_mod_prefix) if not m[2])
    modules = (importlib.import_module(m) for m in modules)

    for module in modules:
        objects = (getattr(module, obj_name) for obj_name in dir(module))
        config_classes = (
            obj for obj in objects if
                isinstance(obj, type) and
                issubclass(obj, Config) and
                obj is not Config
        )
        configs.update(config_classes)
    # END POC Code

    return list(configs)


def parse_repo_config_files():
    repo_config = {}
    for config in all_repository_config_schemas():
        section_name = config.section

        if section_name not in repo_config:
            repo_config.update(config.to_dict())
        else:
            if '{0}_description__'.format(config_item.name) in repo_config[config.section]:
                raise Exception("Error: Two configuration items are declared with the same name Section: {0}, Key: {1}".format(config.section, config.name))

            repo_config[config.section].update(config.to_dict()[config.section])

    return repo_config


def parse_config_files(config_dir):
    """
    Parse all configuration and return a dict with those values.
    """
    config = parse_repo_config_files()
    system_config = parse_system_config_files(config_dir)

    for section, config_items in system_config.items():
        if section not in config:
            print('WARNING: config file contains an unused section: Section: {0}'.format(section))
            config.update[section] = config_items
        else:
            for key, value in config_items:
                if '{0}_description__'.format(key) not in config[section]:
                    print('WARNING: config file contains an unused config entry: Section: {0}, Key{1}'.format(section, key))

                config[section][key] = value

    return config


def format_config():
    """
    Read the configuration definitions from all of the known repositories and return a string that
    can be used as an example config file.

    Example config file:
        transaction:
            to_install_description__: |
                List of packages to be added to the upgrade transaction.
                Signed packages which are already installed will be skipped.
            to_remove_description__: |
                List of packages to be removed from the upgrade transaction
                initial-setup should be removed to avoid it asking for EULA acceptance during upgrade
            to_remove:
                - initial-setup
            to_keep_description__: |
                List of packages to be kept in the upgrade transaction
            to_keep:
                - leapp
                - python2-leapp
                - python3-leapp
                - leapp-repository
                - snactor
    """
    return SafeDumper(yaml.dump(parse_config_files(), dumper=SafeDumper))
