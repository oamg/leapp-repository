from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SELinuxModules


def remove_semanage_customizations():
    # remove SELinux customizations done by semanage -- to be reintroduced after the upgrade
    api.current_logger().info('Removing SELinux customizations introduced by semanage.')

    semanage_options = ['login', 'user', 'port', 'interface', 'module', 'node',
                        'fcontext', 'boolean', 'ibpkey', 'ibendport']
    # permissive domains are handled by porting modules (permissive -a adds new cil module with priority 400)
    for option in semanage_options:
        try:
            run(['semanage', option, '-D'])
        except CalledProcessError:
            continue


# remove custom SElinux modules - to be reinstalled after the upgrade
def remove_custom_modules():
    # go through all SELinuxModules messages -- in theory there should be only one
    for semodules in api.consume(SELinuxModules):
        api.current_logger().info('Removing custom SELinux policy modules. Count: {}'.format(len(semodules.modules)))

        # Form a single "semodule" command to remove all given modules at once.
        # This will help with any inter-dependencies.
        # "semodule" continues removing modules even if it encounters errors - any issues are just printed to stdout
        if semodules.modules:
            command = ['semodule']

            for module in semodules.modules:
                command.extend(['-X', str(module.priority), '-r', module.name])
            try:
                run(command)
            except CalledProcessError as e:
                api.current_logger().warning(
                    'Error removing modules in a single transaction:'
                    '{}\nRetrying -- now each module will be removed separately.'.format(e.stderr)
                )
                # Retry, but remove each module separately
                for module in semodules.modules:
                    try:
                        run(['semodule', '-X', str(module.priority), '-r', module.name])
                    except CalledProcessError as e:
                        api.current_logger().warning('Failed to remove module {} on priority {}: {}'.format(
                                                module.name, module.priority, e.stderr))
                        continue

        remove_udica_templates(semodules.templates)


def remove_udica_templates(templates):
    if not templates:
        return

    api.current_logger().info('Removing "udica" policy templates. Count: {}'.format(len(templates)))
    command = ['semodule']

    for module in templates:
        command.extend(['-X', str(module.priority), '-r', module.name])
    try:
        run(command)
    except CalledProcessError as e:
        api.current_logger().warning(
            'Failed to remove some "udica" policy templates: {}'.format(e.stderr)
        )
