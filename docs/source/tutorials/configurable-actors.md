# Creating configurable actors
Leapp provides (since `framework_version = 6.0`) a built-in way on creating configurable
actors. Therefore, there is no need to use ad-hoc configuration files with an actor-specific
format or introduce environmental variables. Instead, it suffices to declare how your config
should look like, and the framework will take care of locating, parsing and merging config
files so that the config values are provided in a simple, dictionary-like form. User
provides leapp with YAML files stored within `/etc/leapp/actor_conf.d/`. These files
are then read, parsed and type-checked. Afterwards, any actor that declares need to access
specific configuration fields is provided with its own copy of the user-provided configuration.

## Declaring your configuration
Leapp scopes configuration declarations in the same way as it handles libraries.
Configuration available for all actors within a repository is located within
`$repository/configs` whereas actor-specific configuration is searched for
within `$actor_directory/configs`. Configuration declarations are ordinary
Python files, somewhat similar to model declarations. To declare a config field, one
creates a class inheriting from `leapp.actors.config.Config` that declares
the following class attributes:

|  Field   |  Semantics  |
|----------|-------------|
| `section` | Section of the config to which the field belongs |
| `name` | Field name set within the actual config, i.e., the config will contain `name : value` |
| `type_` | Type of the field value. If the user-provided config contains incorrect type, an error will be raised early in leapp execution |
| `default` | Default value for the field, if the field is not set in user-provided config files |
| `description` | String documenting semantics of the config field represented by the class |

For example, to create a configuration field controlling whether network-
interface renaming is managed accessible be all actors, start by creating the
file `$repository/configs/network_cfg.py` with the following contents:
```python
from leapp.actors.config import Config

class EnableNICRenamingChecksField(Config):
    section = 'networking'
    name = 'enable_nic_renaming_checks'
    type_ = fields.Boolean()
    default = True  # Enabled by default
    description = """
        If set to True, actors will check and manage network interfaces getting renamed during the upgrade.
    """
```

## Accessing configuration values
Any actor that requires reading the `networking.enable_nic_renaming_checks` configuration
value provided by the user must then declare access to this config value within its
definition. After declaring its configuration access, the actor can access the
corresponding config field using `api.current_actor().config[$section][$field_name]`
where `$section` is the value of the `$section` and `$field_name` are the values
of `section` and `name` class attribute, respectively.
For example, given an actor defined in `scan_source_nic_names/actor.py`,
we would have:
```python
from leapp.actors import Actor
from leapp.configs.common.network_cfg import EnableNICRenamingChecksField
from leapp.models import SourceNICsInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanSourceNICs(Actor):
    """
    Gather information about NICs installed on the source system
    """

    name = 'scan_source_nics'
    config_schemas = (EnableNICRenamingChecksField,)  # Declare what configuration we are accessing
    consumes = ()
    produces = (SourceNICsInfo)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        config_value = api.current_actor().config['networking']['enable_nic_renaming_checks']
        # Do something with config value
```

Not that, naturally, one can use the `api.current_actor().config` dictionary from any
library as well.

## Providing actors with configuration
Framework scans for any YAML files (directly) under `/etc/leapp/actor_conf.d/`. The
structure of these YAML files is the following:
```YAML
sectionA:
  field1: value1
  field2: value2
  field3: value3

sectionB:
  field1: value1
  field2: value2
  field3: value3
```

Therefore, to turn off NIC renaming checks using the
`networking.enable_nic_renaming_checks` field defined above, one would create,
e.g., a file named `/etc/leapp/actors.conf.d/networking.yaml` with the following
content:
```yaml
networking:
  enable_nic_renaming_checks: False
```
