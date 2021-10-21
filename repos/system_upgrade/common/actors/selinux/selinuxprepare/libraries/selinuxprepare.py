from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.models import SELinuxModules


def remove_semanage_customizations():
    # remove SELinux customizations done by semanage -- to be reintroduced after the upgrade
    api.current_logger().info('Removing SELinux customizations introduced by semanage.')

    semanage_options = ["login", "user", "port", "interface", "module", "node",
                        "fcontext", "boolean", "ibpkey", "ibendport"]
    # permissive domains are handled by porting modules (permissive -a adds new cil module with priority 400)
    for option in semanage_options:
        try:
            run(['semanage', option, '-D'])
        except CalledProcessError:
            continue


def remove_custom_modules():
    # remove custom SElinux modules - to be reinstalled after the upgrade
    for semodules in api.consume(SELinuxModules):
        api.current_logger().info("Removing custom SELinux policy modules. Count: %d", len(semodules.modules))

        failed = remove_custom_modules_helper(semodules.modules)
        # retry removing in reverse order
        api.current_logger().info("Some modules couldn't be removed, retrying. Count: %d", len(failed))
        if failed:
            remove_custom_modules_helper(reversed(failed))


def remove_custom_modules_helper(selinux_modules):
    # store modules that couldn't be removed so that we can retry
    failed = []

    for module in selinux_modules:
        api.current_logger().info("Removing %s on priority %d.", module.name, module.priority)
        try:
            run(['semodule',
                 '-X', str(module.priority),
                 '-r', module.name
                 ]
                )
        except CalledProcessError as e:
            failed.append(module)
            api.current_logger().warning("Failed to remove module %s on priority %d: %s",
                                         module.name, module.priority, str(e.stderr))
    return failed
