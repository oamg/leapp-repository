import functools
import os
import sys

import six

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api, CalledProcessError, config, run, STDOUT
from leapp.utils.deprecation import deprecated


def parse_config(cfg=None, strict=True):
    """
    Applies a workaround to parse a config file using py3 AND py2

    ConfigParser has a new def to read strings/files in Py3, making
    the old ones (Py2) obsoletes, these function was created to use the
    ConfigParser on Py2 and Py3

    :type cfg: str
    :type strict: bool
    """
    if six.PY3:
        parser = six.moves.configparser.ConfigParser(strict=strict)  # pylint: disable=unexpected-keyword-arg
    else:
        parser = six.moves.configparser.ConfigParser()

    # we do not handle exception here, handle with it when these function is called
    if cfg and six.PY3:
        # Python 3
        if isinstance(cfg, six.string_types):
            parser.read_string(cfg)
        else:
            parser.read_file(cfg)
    elif cfg:
        # Python 2
        from cStringIO import StringIO  # pylint: disable=import-outside-toplevel
        if isinstance(cfg, six.string_types):
            parser.readfp(StringIO(cfg))  # pylint: disable=deprecated-method
        else:
            parser.readfp(cfg)  # pylint: disable=deprecated-method
    return parser


def makedirs(path, mode=0o777, exists_ok=True):
    mounting._makedirs(path=path, mode=mode, exists_ok=exists_ok)


@deprecated(since='2022-02-03', message=(
        'The "apply_yum_workaround" function has been deprecated, use "DNFWorkaround" '
        'message as used in the successive "RegisterYumAdjustment" actor.'
    )
)
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
            message='Failed to execute script to apply yum adjustment. Message: {}'.format(str(e))
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
    if fd_type != STDOUT and not config.is_debug():
        return
    target = sys.stdout if fd_type == STDOUT else sys.stderr
    if sys.version_info > (3, 0):
        os.writev(target.fileno(), [buf])
    else:
        target.write(buf)


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
    # third parameter has changed in Python 3.12
    if sys.version_info >= (3, 12):
        api.current_logger().warning(
            'While trying to remove directories: %s failed at %s with an exception %s message: %s',
            func.__name__, path, exc_info[0].__name__, exc_info[1]
        )
    else:
        api.current_logger().warning(
            'While trying to remove directories: %s failed at %s with an exception %s message: %s',
            func.__name__, path, type(exc_info).__name__, str(exc_info)
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
                    # Broad exception handler to handle all cases however, swallowed, to avoid losing the original
                    # error. Logging for debuggability.
                    api.current_logger().warning('Caught and swallowed an exception during cleanup.', exc_info=True)
                raise  # rethrow original exception

        return wrapper

    return clean_wrapper


def read_file(path):
    """
    Reads the file specified by path in text mode and returns the contents.
    """
    with open(path, 'r') as f:
        return f.read()


def _require_exactly_one_message_of_type(model_class, error_callback=None):
    """
    Consume and return exactly one message of the given type, error if there are none or more than one available.

    Calls ``error_callback`` if there are none or more than one messages available of the requested type
    with a string describing the error condition.

    Note: this function is private, experimental and will likely be subject to change.

    :param model_class: Message type to consume
    :param Callable[[str], None] error_callback: Callback to call when error condition arises, e.g., raising the
                                                 StopActorExecutionError (default).
    """
    def default_callback(msg):
        raise StopActorExecutionError(msg)

    if not error_callback:
        error_callback = default_callback

    model_instances = api.consume(model_class)
    model_instance = next(model_instances, None)
    if not model_instance:
        msg = 'Exactly one {cls_name} message of type is required, however, none was received.'
        msg = msg.format(cls_name=model_class.__name__)
        error_callback(msg)

    next_instance = next(model_instances, None)
    if next_instance:
        msg = 'Exactly one {cls_name} message is required, however, more than one messages were received.'
        msg = msg.format(cls_name=model_class.__name__)
        error_callback(msg)

    return model_instance


def _require_some_message_of_type(model_class, error_callback=None):
    """
    Consume and return one message of the given type, error if there are no messages available.

    Calls ``error_callback`` if there are no messages available of the requested type
    with a string describing the error condition.

    Note: this function is private, experimental and will likely be subject to change.

    :param model_class: Message type to consume
    :param Callable[[str], None] error_callback: Callback to call when error condition arises, e.g., raising the
                                                 StopActorExecutionError (default).
    """
    def default_callback(msg):
        raise StopActorExecutionError(msg)

    if not error_callback:
        error_callback = default_callback

    model_instances = api.consume(model_class)
    model_instance = next(model_instances, None)
    if not model_instance:
        msg = 'Exactly one {cls_name} message of type is required, however, none was received.'
        msg = msg.format(cls_name=model_class.__name__)
        error_callback(msg)

    return model_instance
