# Troubleshooting and Debugging
This tutorial covers the different ways of debugging and troubleshooting the in-place upgrade process.

## Debug logs
The leapp framework, as well as actors in the in-place upgrade repositories log important events during the upgrade. Debug logs are written to `/var/log/leapp/leapp-preupgrade.log` or `/var/log/leapp/leapp-upgrade.log`.


```{note}
Debug logs are not enabled by default, run `leapp` with the `--debug` option to enable debug logging.
```

## Troubleshooting with leapp-inspector
The leapp-inspector tool is unofficial and unstable tool helping with debugging
based on data stored inside the leapp.db audit database.

In addition to extensive logging, leapp writes a lot of information into it's database at `/var/lib/leapp/leapp.db`, such as messages and their contents, executed actors, logs and messages produced by individual actors and more.
To view data in the database you can use the leapp-inspector tool, see the [docs](https://github.com/oamg/snippets/tree/main/scripts/leappinspector) for installation instructions.

```{note}
`leapp-inspector` does not have to be installed on the system being upgraded. You can copy `leapp.db` to another system and use `leapp-inspector` there. In such case specify path to `leapp.db` using the `--db` option.
```

```{warning}
The leapp-inspector tool is not official and it is unstable. However, we are
using it on daily bases as it's very useful for debugging. So we are sharing
the information about the tool with you. Just be aware that everything around
the tool can be changed without any warnings.
```

### Usage
See `leapp-inspector --help` for all options, it's well documented.

#### Inspect Specific Execution
By default, `leapp-inspector` shows information about the most recent leapp execution.
To inspect a specific execution:

1. List the executions and find the ID of the desired execution.
    ```shell
    [root@-20250129142956 ~]$ leapp-inspector executions
    ######################################################################
                             Executions of Leapp
    ######################################################################
    Execution                            | Timestamp
    ------------------------------------ | ---------------------------
    58c2167d-d747-4a98-8660-af457e32711e | 2025-01-29T13:48:12.119698Z
    42340943-e06c-4ff7-a2e6-9601eb76bbe0 | 2025-01-29T15:10:10.892776Z
    ```
2. Add the `--context <execution id>` parameter in subsequent commands.

## Debugging Code
[The Python Debugger](https://docs.python.org/3/library/pdb.html) - `pdb` can be used for standard debugging.
1. Before running leapp insert the following line to set a breakpoint in the code:
    ```python
    import pdb; pdb.set_trace()
    ```
2. Run leapp and wait for `pdb` prompt to appear.
3. Debug. See the `pdb` docs on how to use it.
4. To continue the upgrade use the `continue` (or `c`) command.

## Inspecting the Target Userspace Container During an Upgrade
Sometimes it's useful to interactively inspect the target userspace container during the upgrade, e.g. to ensure required files are present. The following steps describe how to enter the container:

1. Set a breakpoint at the desired point in the code as described in the previous section
2. Open another terminal session on the machine being upgraded
3. Run the upgrade in the first terminal
4. When the breakpoint is reached (`pdb` prompt is displayed), enter the container in the second terminal. As the container needs a lot of variables passed in, the easiest way to do this is to find the `systemd-nspawn` command that leapp used to enter the container in the debug output in the first terminal. In the following example the first line is the command:
    ```
    2025-01-29 13:49:24.691 DEBUG    PID: 40673 leapp.workflow.TargetTransactionFactsCollection.target_userspace_creator: External command has finished: ['systemd-nspawn', '--register=no', '--quiet', '--keep-unit', '--capability=all', '-D', '/var/lib/leapp/scratch/mounts/root_/system_overlay', '--setenv=LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE=1', '--setenv=LEAPP_NO_RHSM=1', '--setenv=LEAPP_UNSUPPORTED=1', '--setenv=LEAPP_HOSTNAME=leapp-20250129142956', '--setenv=LEAPP_EXPERIMENTAL=0', '--setenv=LEAPP_NO_RHSM_FACTS=1', '--setenv=LEAPP_TARGET_PRODUCT_CHANNEL=ga', '--setenv=LEAPP_UPGRADE_PATH_TARGET_RELEASE=9.6', '--setenv=LEAPP_UPGRADE_PATH_FLAVOUR=default', '--setenv=LEAPP_IPU_IN_PROGRESS=8to9', '--setenv=LEAPP_EXECUTION_ID=58c2167d-d747-4a98-8660-af457e32711e', '--setenv=LEAPP_COMMON_TOOLS=:/etc/leapp/repos.d/system_upgrade/common/tools:/etc/leapp/repos.d/system_upgrade/el8toel9/tools', '--setenv=LEAPP_COMMON_FILES=:/etc/leapp/repos.d/system_upgrade/common/files:/etc/leapp/repos.d/system_upgrade/el8toel9/files', '--setenv=LEAPP_DEVEL_DATABASE_SYNC_OFF=1', 'dnf', 'install', '-y', '--setopt=module_platform_id=platform:el9', '--setopt=keepcache=1', '--releasever', '9.6', '--installroot', '/el9target', '--disablerepo', '*', '--enablerepo', 'BASEOS', '--enablerepo', 'APPSTREAM', 'util-linux', 'kpatch-dnf', 'dnf', 'dnf-command(config-manager)', '-v', '--disableplugin', 'subscription-manager']
    2025-01-29 13:49:24.692 DEBUG    PID: 40673 leapp.workflow.TargetTransactionFactsCollection.target_userspace_creator: External command has started: ['umount', '-fl', '/var/lib/leapp/scratch/mounts/root_/system_overlay/el9target']
    2025-01-29 13:49:24.703 DEBUG    PID: 40673 leapp.workflow.TargetTransactionFactsCollection.target_userspace_creator: External command has finished: ['umount', '-fl', '/var/lib/leapp/scratch/mounts/root_/system_overlay/el9target']
    2025-01-29 13:49:24.704 DEBUG    PID: 40673 leapp.workflow.TargetTransactionFactsCollection.target_userspace_creator: External command has started: ['rm', '-rf', '/var/lib/leapp/scratch/mounts/root_/system_overlay/el9target']
    2025-01-29 13:49:24.709 DEBUG    PID: 40673 leapp.workflow.TargetTransactionFactsCollection.target_userspace_creator: External command has finished: ['rm', '-rf', '/var/lib/leapp/scratch/mounts/root_/system_overlay/el9target']
    > /etc/leapp/repos.d/system_upgrade/common/actors/targetuserspacecreator/libraries/userspacegen.py(569)_copy_certificates()
    -> files_owned_by_rpms = _get_files_owned_by_rpms(target_context, '/etc/pki', recursive=True)
    (Pdb)
    ```
    Command will contain another shell command at the end (`dnf install ...` in this example) that needs to be stripped. Then run the command in the second terminal to enter and inspect the container:
    ```bash
    # WARNING: DO NOT BLINDLY COPY THIS COMMAND, THE VARIABLE VALUES ARE UNIQUE FOR AN UPGRADE
    systemd-nspawn --register=no --quiet --keep-unit --capability=all -D /var/lib/leapp/scratch/mounts/root_/system_overlay --setenv=LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE=1 --setenv=LEAPP_NO_RHSM=1 --setenv=LEAPP_UNSUPPORTED=1 --setenv=LEAPP_HOSTNAME=leapp-20250129142956 --setenv=LEAPP_EXPERIMENTAL=0 --setenv=LEAPP_NO_RHSM_FACTS=1 --setenv=LEAPP_TARGET_PRODUCT_CHANNEL=ga --setenv=LEAPP_UPGRADE_PATH_TARGET_RELEASE=9.6 --setenv=LEAPP_UPGRADE_PATH_FLAVOUR=default --setenv=LEAPP_IPU_IN_PROGRESS=8to9 --setenv=LEAPP_EXECUTION_ID=58c2167d-d747-4a98-8660-af457e32711e --setenv=LEAPP_COMMON_TOOLS=:/etc/leapp/repos.d/system_upgrade/common/tools:/etc/leapp/repos.d/system_upgrade/el8toel9/tools --setenv=LEAPP_COMMON_FILES=:/etc/leapp/repos.d/system_upgrade/common/files:/etc/leapp/repos.d/system_upgrade/el8toel9/files --setenv=LEAPP_DEVEL_DATABASE_SYNC_OFF=1
    ```
5. To continue the upgrade, exit the container and resume the debugger (`continue` or `c`).


## Debugging Inside Initramfs
One of the biggest debugging challenges is exploring something in initramfs stage, as currently there is no network connectivity.

```{note}
When working in initramfs stage you will need a serial console. There is not network connectivity, SSH does not work.
```


1. If not already in the dracut emergency console, such as in case of an error, a breakpoint can be set to force leapp to enter the console. The following breakpoints are available:

    | Breakpoint        | Description                                                    |
    |-----------        |------------                                                    |
    | leapp-pre-upgrade | Break right before running leapp in initramfs                  |
    | leapp-upgrade     | Break right after LEAPP upgrade, before post-upgrade leapp run |
    | leapp-finish      | Break after LEAPP save_journal (upgrade initramfs end)         |

    The breakpoint has to be passed using the `rd.upgrade.break=` argument on the kernel command line. There are (at least) 2 ways to do this:
    - Modify the cmdline in GRUB, press Ctrl-X when the Upgrade initramfs is selected and add the argument at the end of the line starting with `LINUX=`
    - Modify the [addupgradebootentry actor](https://github.com/oamg/leapp-repository/blob/master/repos/system_upgrade/common/actors/addupgradebootentry/libraries/addupgradebootentry.py#L23) to add the argument

2. Once in the emergency shell, you may want to use some of the utilities provided in `$CWD/leapp_debug_tools.sh` (should be automatically sourced):
    - `leapp_dbg_mount` - mounts `/sysroot` as read/write
    - `leapp_dbg_source` - the set of commands available in the emergency shell is very limited, this sets PATH and LD_LIBRARY_PATH to be able to run commands from `/sysroot`
    - `leapp_dbg_chroot` - change root into `/sysroot`

3. Inspect/modify `/sysroot` as needed
4. To continue the upgrade, exit the shell

