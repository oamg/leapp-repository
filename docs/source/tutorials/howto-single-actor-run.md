# Running a single Actor

During development or debugging of actors there may appear a need of running single actor instead of the entire workflow. The advantages of such approach include:
- **Time and resource efficiency** - Running the entire workflow takes time and resources. Source system is scanned, information is collected and stored, in-place upgrade process goes through several phases. All these actions take time, actors are run multiple times during debugging or development process, so preparing single actor execution lets us save time.
- **Isolation of problem** - When debugged issue is related to single actor, this approach allows to isolate the issue without interference from other actors.


```{hint}
In practice, running a single actor for debugging does not have to be the best way to start when you do not have much experience with Leapp and IPU yet. However, in some cases it's still very valuable and helpful.
```

The execution of an actor using the `snactor` tool seems simple. In case of system upgrade leapp repositories it's not so straightforward and
it can be quite complicated. In this guide we share our experience how to use `snactor` correctly, describing typical problems that developers hit.

There are two main approaches:
- **Running an actor with an empty or non-existent leapp database** -- applicable when a crafted data (or no data at all) is needed. Usually during development.
- **Running an actor with leapp database filled by previous leapp execution** -- useful for debugging when the leapp.db file is available and want to run the actor in the same context as it has been previously executed when an error occurred.

```{note}
The leapp database refers to the `leapp.db` file. In case of using snactor, it's by default present in the `.leapp` directory of the used leapp repository
scope.
```

````{tip}
Cleaning the database can be managed with `snactor` tool command:
```shell
snactor messages clear
```
In other way, the database file can be also simply removed instead of using snactor.
````


Since an actor seems to be an independent piece of code, there is a dependency chain to resolve inside a workflow, especially around consumed messages and configuration which have to be resolved. When running entire In-Place Upgrade process, those dependencies needed for each actor are satisfied by assignment of each actor to specific phase, where actors emit and consume messages in desired sequence. Single actor usually needs specific list of such requirements, which can be fulfilled by manual preparation of this dependency chain. This very limited amount of resources needed for single actor can be called minimal context.


## Running a single actor with minimal context

It is possible to run a single actor without proceeding with `leapp preupgrade` machinery.
This solution is based on the snactor tool. However, this solution requires minimal context to run.

As mentioned before and described in [article](https://leapp.readthedocs.io/en/stable/building-blocks-and-architecture.html#architecture-overview)
about workflow architecture, most of the actors are part of the produce/consume chain of messages. Important step in this procedure is to recreate the sequence of actors to be run to fulfill a chain of dependencies and provide necessary variables.

Let's explain these steps based on a real case. The following example will be based on the `scan_fips` actor.


### Initial configuration

All actors (even those which are not depending on any message emitted by other actors) depend on some initial configuration which is provided by the `ipu_workflow_config` [actor](https://github.com/oamg/leapp-repository/blob/main/repos/system_upgrade/common/actors/ipuworkflowconfig/libraries/ipuworkflowconfig.py). No matter what actor you would like to run, the first step is always to run the `ipu_workflow_config` actor.

Due to some missing initial variables, which usually are set by the framework, those variables need to be exported manually. Note that following vars are example ones, adjust them to your needs depending on your system configuration:
```shell

export LEAPP_UPGRADE_PATH_FLAVOUR=default
export LEAPP_UPGRADE_PATH_TARGET_RELEASE=9.8
export LEAPP_TARGET_OS=9.8
```

The `ipu_workflow_config` actor produces `IPUWorkflow` message, which contains all required initial config, so at the beginning execute:

```shell
snactor run ipu_workflow_config --print-output --save-output
```

```{note}
Option `--save-output` is necessary to preserve output of this command in Leapp database. Without saving the message, it will not be available for other actors. Option *--print-output* is optional.
```

### Resolving actor's message dependencies

All basic information what actor consumes and produce can be found in each `actor.py` [code](https://github.com/oamg/leapp-repository/blob/main/repos/system_upgrade/common/actors/scanfips/actor.py#L13-L14). In case of `scan_fips` actor it's:

```shell
    consumes = (KernelCmdline,)
    produces = (FIPSInfo,)
```

This actor consumes one message and produces another. Now we need to track the consumed message, which is `KernelCmdline`. Grep the cloned repository to find that the actor which produces such [message](https://github.com/oamg/leapp-repository/blob/main/repos/system_upgrade/common/actors/scankernelcmdline/actor.py#L14) is `scan_kernel_cmdline`. 

```shell
snactor run scan_kernel_cmdline --print-output --save-output --actor-config IPUConfig
```

```{note}
Important step here is to point out what actor config needs to be used, `IPUConfig` in that case.
This parameter needs to be specified every time you want to run an actor, pointing to proper configuration.
```

This [scan_kernel_cmdline](https://github.com/oamg/leapp-repository/blob/main/repos/system_upgrade/common/actors/scankernelcmdline/actor.py#L13) doesn't consume anything: `consumes = ()`. So finally the desired actor can be run:

```shell
snactor run scan_fips --print-output --save-output --actor-config IPUConfig
```

### Limitations
Note that not all cases will be as simple as the presented one, sometimes actors depend on multiple messages originating from other actors, requiring longer session of environment recreation.

Also actors designed to run on other architectures will not be able to run.

## Run single actor with existing database

In contrast to the previous paragraph, where we operated only on self-created minimal context, the tutorial below will explain how to work with existing or provided context.
Sometimes - especially for debugging and reproduction of the bug it is very convenient to use provided Leapp database *leapp.db*. This is a file containing all information needed to run Leapp framework on a system, including messages and configurations. Usually all necessary environment for actors is set up by
first run of `leapp preupgrade` command, when starting from scratch. In this case, we already have `leapp.db` (e.g. transferred from other system) database file.

Every new run of `leapp` command creates another entry in the database. It creates
another row in execution table with specific ID, so each context can be easily tracked and
reproduced.

See the list of executions using the [leapp-inspector](https://leapp-repository.readthedocs.io/latest/tutorials/troubleshooting-debugging.html#troubleshooting-with-leapp-inspector) tool.

```shell
leapp-inspector --db path/to/leapp.db executions
```
Example output:
```shell
##################################################################
                         Executions of Leapp
##################################################################
Execution                            | Timestamp
------------------------------------ | ---------------------------
d146e105-fafd-43a2-a791-54e141eeab9c | 2025-11-26T19:39:20.563594Z
b7fd5dca-a49f-4af7-b70c-8bbcc28a4338 | 2025-11-26T19:39:38.034070Z
50b5289f-be4d-4206-a6e0-73e3caa1f9ed | 2025-11-26T19:41:40.401273Z

```


To determine which context (execution) `leapp` will run, there are two variables: `LEAPP_DEBUG_PRESERVE_CONTEXT`
and `LEAPP_EXECUTION_ID`. When the `LEAPP_DEBUG_PRESERVE_CONTEXT` is set to 1 and the environment has
`LEAPP_EXECUTION_ID` set, the `LEAPP_EXECUTION_ID` is not overwritten with snactor's execution ID.
This allows the developer to run actors in the same way as if the actor was run during the last leapp's
execution, thus, avoiding to rerun the entire upgrade process.


Set variables:
```shell

export LEAPP_DEBUG_PRESERVE_CONTEXT=1
export LEAPP_EXECUTION_ID=50b5289f-be4d-4206-a6e0-73e3caa1f9ed
```

Run desired actors or the entire upgrade process safely now. Output will not be preserved as another context entry.
```shell

snactor run --config /etc/leapp/leapp.conf --actor-config IPUConfig <ActorName> --print-output
```

```{note}
Point to `leapp.conf` file with *--config* option. By default this file is located in `/etc/leapp/` and, among others, it contains Leapp database (`leapp.db`) location. When working with given database, either adjust configuration file or place database file in default location.
```

### Limitations

Even though the context was provided, it is not possible to run actors which are designed for different architecture than source system.
