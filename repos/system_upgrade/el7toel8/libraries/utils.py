import functools
import sys

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import STDOUT, CalledProcessError, api, config, run


def makedirs(path, mode=0o777, exists_ok=True):
    mounting._makedirs(path=path, mode=mode, exists_ok=exists_ok)


def apply_yum_workaround(context=None):
    """
    Applies a workaround on the system to allow the upgrade to succeed for yum/dnf.
    """
    yum_script_path = api.get_tool_path('handleyumconfig')
    if not yum_script_path:
        raise StopActorExecutionError(
            message='Failed to find mandatory script to apply',
            details=reinstall_leapp_repository_hint()
        )
    cmd = ['/bin/bash', '-c', yum_script_path]

    try:
        context = context or mounting.NotIsolatedActions(base_dir='/')
        context.call(cmd)
    except OSError as e:
        raise StopActorExecutionError(
            message='Failed to exceute script to apply yum adjustment. Message: {}'.format(str(e))
        )
    except CalledProcessError as e:
        raise StopActorExecutionError(
            message='Failed to apply yum adjustment. Message: {}'.format(str(e))
        )


def logging_handler(fd_info, buf):
    """
    Custom log handler to always show stdout to console and stderr only in DEBUG mode
    """
    (_unused, fd_type) = fd_info

    if fd_type == STDOUT:
        sys.stdout.write(buf)
    else:
        if config.is_debug():
            sys.stderr.write(buf)


def reinstall_leapp_repository_hint():
    """
    Convenience function for creating a detail for StopActorExecutionError with a hint to reinstall the
    leapp-repository package
    """
    return {
        'hint': 'Try to reinstall the `leapp-repository` package.'
    }


def report_and_ignore_shutil_rmtree_error(func, path, exc_info):
    """
    Helper function for shutil.rmtree to only report errors but don't fail.
    """
    api.current_logger().warn(
        'While trying to remove directories: %s failed at %s with an exception %s message: %s',
        func.__name__, path, exc_info[0].__name__, exc_info[1]
    )


def call_with_oserror_handled(cmd):
    """
    Perform run with already handled OSError for some convenience.
    """
    try:
        run(cmd)
    except OSError as e:
        if cmd:
            raise StopActorExecutionError(
                message=str(e),
                details={
                    'hint': 'Please ensure that {} is installed and executable.'.format(cmd[0])
                }
            )
        else:
            raise StopActorExecutionError(
                message='Failed to execute command {} with: {}'.format(''.join(cmd), str(e))
            )


def call_with_failure_hint(cmd, hint):
    """
    Perform `run` which handles OSError through call_with_oserror_handled and transforms CalledProcessError to a
    StopActorExecutionError with a hint given by the caller.
    """
    try:
        call_with_oserror_handled(cmd)
    except CalledProcessError as e:
        raise StopActorExecutionError(
            message='Failed to execute command `{}`. Error: {}'.format(' '.join(cmd), str(e)),
            details={hint: hint}
        )


def clean_guard(cleanup_function):
    """
    Decorator to handle any exception going through and running cleanup tasks through the given cleanup_function
    parameter.
    """
    def clean_wrapper(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception:  # Broad exception handler to handle all cases but rethrows
                api.current_logger().debug('Clean guard caught an exception - Calling cleanup function.')
                try:
                    cleanup_function(*args, **kwargs)
                except Exception:  # pylint: disable=broad-except
                    # Broad exception handler to handle all cases however, swallowed, to avoid loosing the original
                    # error. Logging for debuggability.
                    api.current_logger().warn('Caught and swallowed an exception during cleanup.', exc_info=True)
                raise  # rethrow original exception
        return wrapper
    return clean_wrapper
