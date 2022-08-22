import errno
import itertools
import os
import shutil
from collections import namedtuple

from leapp.libraries.common.config import get_all_envs
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api, CalledProcessError, run

# Using ALWAYS_BIND will crash the upgrade process if the file does not exist.
# Consider instead adding an entry to the ScanFilesToCopyIntoTargetSystem actor that
# conditionaly (only if it exists) creates CopyFile message to the TargetUserspaceCreator.
ALWAYS_BIND = []

ErrorData = namedtuple('ErrorData', ['summary', 'details'])


class MountingMode(object):
    """
    MountingMode are types of mounts supported by the library
    """
    BIND = 'bind'
    """ Used for bind mounts """
    OVERLAY = 'overlay'
    """ Used for overlayfs mounts """
    LOOP = 'loop'
    """ Used for loop mounts """
    FSTYPE = 'fstype'
    """ Used to mount specific filesystem types such as procfs, sysfs etc """
    NONE = 'none'
    """ Used when no actual mount call needs to be issued """


def _makedirs(path, mode=0o777, exists_ok=True):
    """ Helper function which extends os.makedirs with exists_ok on all versions of python. """
    try:
        os.makedirs(path, mode=mode)
    except OSError:
        if not exists_ok or not os.path.isdir(path):
            raise


class MountError(Exception):
    """ Exception that is thrown when a mount related operation failed """

    def __init__(self, message, details):
        super(MountError, self).__init__(message)
        self.details = details


class IsolationType(object):
    """ Implementations for the different isolated actions types """
    class _Implementation(object):
        """ Base class for all isolated actions """

        def __init__(self, target, **kwargs):
            self.target = target

        def create(self):
            """ Create the isolation context """
            pass

        def close(self):
            """ Release the isolation context """
            pass

        def make_command(self, cmd):
            """ Transform the given command to the isolated environment """
            return cmd

    class NSPAWN(_Implementation):
        """ systemd-nspawn implementation """

        def __init__(self, target, binds=(), env_vars=None):
            super(IsolationType.NSPAWN, self).__init__(target=target)
            self.binds = list(binds) + ALWAYS_BIND
            self.env_vars = env_vars or get_all_envs()

        def make_command(self, cmd):
            """ Transform the command to be executed with systemd-nspawn """
            binds = ['--bind={}'.format(bind) for bind in self.binds]
            setenvs = ['--setenv={}={}'.format(env.name, env.value) for env in self.env_vars]
            final_cmd = ['systemd-nspawn', '--register=no', '--quiet']
            if get_source_major_version() != '7':
                # TODO: check whether we could use the --keep unit on el7 too.
                # in such a case, just add line into the previous solution..
                # TODO: the same about --capability=all
                final_cmd += ['--keep-unit', '--capability=all']
            return final_cmd + ['-D', self.target] + binds + setenvs + cmd

    class CHROOT(_Implementation):
        """ chroot implementation """

        def __init__(self, target):
            super(IsolationType.CHROOT, self).__init__(target)
            self.context = None

        def create(self):
            """ Create the necessary context for chroot based isolation """
            self.close()
            self.context = self._create_context()
            next(self.context)

        def _create_context(self):
            """ This will mount /proc, /sys and /dev for chroot executions """
            with TypedMount('proc', 'proc', os.path.join(self.target, 'proc')):
                with TypedMount('sysfs', 'sys', os.path.join(self.target, 'sys')):
                    with BindMount('/dev', os.path.join(self.target, 'dev')):
                        yield

        def close(self):
            """ Releasing the context and perform unmounting """
            if self.context:
                next(self.context)
            self.context = None

        def make_command(self, cmd):
            """ Transform the command to be executed in the chrooted environment """
            return [
                'chroot', self.target
            ] + cmd

    class NONE(_Implementation):
        """ Execute the given commands and perform the given operations on the real system and not isolated. """


class IsolatedActions(object):
    """ This class allows to perform actions in a manner as if the given base_dir would be the current root """

    _isolated = True

    def __init__(self, base_dir, implementation, **kwargs):
        self.base_dir = base_dir
        self.type = implementation(base_dir, **kwargs)

    def __enter__(self):
        self.type.create()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.type.close()

    def full_path(self, path):
        """
        Transform the path given to be prefixed with the base_dir, to get the real path on the system.

        The function is secured, so it is not possible to return path outside
        of the self.base_dir directory.

        Example: self.base_dir = '/var/lib/leapp/scratch/userspace'
                 path = '/etc/yum.repos.d/redhat.repo'
                 The result would be: /var/lib/leapp/scratch/userspace/etc/yum.repos.d/redhat.repo
        """
        return os.path.join(self.base_dir, os.path.abspath(path).lstrip('/'))

    def open(self, path, *args, **kwargs):
        """
        Open the path given as if it would be the real system.

        The only difference between this function and the python builtin open is the fact that the path uses
        self.full_path to translate the passed path argument. All other arguments are passed through
        """
        return open(self.full_path(path), *args, **kwargs)

    def call(self, cmd, *args, **kwargs):
        """ Running the given command using the leapp.libraries.stdlib.run function in a isolated manner. """
        return run(self.type.make_command(cmd), *args, **kwargs)

    def remove(self, path):
        """
        Removes the given file as it would be on the real system.
        """
        os.unlink(self.full_path(path))

    def remove_tree(self, path):
        """
        Removes the given directory recursively inside the isolated environment
        as it would be on the real system.

        If the destination doesn't exist, nothing happens.
        """
        try:
            shutil.rmtree(self.full_path(path))
        except EnvironmentError as e:
            # this is recommended way to handle it in Py2 & Py3
            if e.errno != errno.ENOENT:
                raise

    def mkdir(self, path, mode=0o777):
        """
        Creates the given path as it would be on the real system.
        """
        os.mkdir(self.full_path(path), mode=mode)

    def makedirs(self, path, mode=0o777, exists_ok=True):
        """
        Creates the whole path recursively for any missing part.
        """
        _makedirs(path=self.full_path(path), mode=mode, exists_ok=exists_ok)

    def copytree_to(self, src, dst):
        """
        Recursively copy an entire directory tree rooted at src. The destination directory,
        named by dst, must not already exist; it will be created as well as missing parent directories.

        The destination directory is considered to be in the isolated environment.
        The source directory is considered to be on the current system root.
        """
        shutil.copytree(src, self.full_path(dst))

    def copytree_from(self, src, dst):
        """
        Recursively copy an entire directory tree rooted at src. The destination directory,
        named by dst, must not already exist; it will be created as well as missing parent directories.

        The destination directory is considered to be on the current system root.
        The source directory is considered to be in the isolated environment.
        """
        shutil.copytree(self.full_path(src), dst)

    def copy_to(self, src, dst):
        """
        Copy the file src to the file or directory dst. If dst is a directory, a file with the same basename
        as src is created (or overwritten) in the directory specified. Permission bits are copied. src and dst
        are path names given as strings.
        copy_to also attempts to preserve file metadata.

        The source is expected to be on the current system.
        The destination is expected to be in the isolated environment.
        """
        shutil.copy2(src, self.full_path(dst))

    def copy_from(self, src, dst):
        """
        Copy the file src to the file or directory dst. If dst is a directory, a file with the same basename
        as src is created (or overwritten) in the directory specified. Permission bits are copied. src and dst
        are path names given as strings.
        copy_to also attempts to preserve file metadata.

        The source is expected to be in the isolated environment.
        The destination is expected to be on the current system.
        """
        shutil.copy2(self.full_path(src), dst)

    @classmethod
    def is_isolated(cls):
        """
        Tell whether the context is isolated or not.

        All classes except NotIsolatedActions return True.
        """
        return cls._isolated


class ChrootActions(IsolatedActions):
    """ Isolation with chroot """

    def __init__(self, base_dir):
        super(ChrootActions, self).__init__(base_dir=base_dir, implementation=IsolationType.CHROOT)


class NspawnActions(IsolatedActions):
    """ Isolation with systemd-nspawn """

    def __init__(self, base_dir, binds=(), env_vars=None):
        super(NspawnActions, self).__init__(
            base_dir=base_dir, implementation=IsolationType.NSPAWN, binds=binds, env_vars=env_vars)


class NotIsolatedActions(IsolatedActions):
    """ Non isolated executed. """
    _isolated = False

    def __init__(self, base_dir):
        super(NotIsolatedActions, self).__init__(base_dir=base_dir, implementation=IsolationType.NONE)


class MountConfig(object):
    """ Options for Mount """
    _Options = namedtuple('_Options', ('should_create', 'should_cleanup'))
    AttachOnly = _Options(should_create=False, should_cleanup=False)
    """ Do not perform any mount operations, and do not clean up afterwards """
    Attach = _Options(should_create=False, should_cleanup=True)
    """ Do not perform any mount operations, however cleanup afterwards """
    MountOnly = _Options(should_create=True, should_cleanup=False)
    """ Create all necessary directories and perform mount calls, but do not cleanup afterwards """
    Mount = _Options(should_create=True, should_cleanup=True)
    """ Create all necessary directories and perform mount calls and cleanup afterwards """


class MountingBase(object):
    """ Base class for all mount operations """

    def __init__(self, source, target, mode, config=MountConfig.Mount):
        self._mode = mode
        self.source = source
        self.target = target
        self._config = config
        self.additional_directories = ()

    def _mount_options(self):
        """
        Options to use with the mount call, individual implementations may override this function to return the
        correct parameters
        """
        return ['-o', self._mode, self.source]

    def chroot(self):
        """ Create a ChrootActions instance for this mount """
        return ChrootActions(self.target)

    def nspawn(self):
        """ Create a NspawnActions instance for this mount """
        return NspawnActions(self.target)

    def real(self):
        """ Create a NotIsolatedActions instance for this mount """
        return NotIsolatedActions(self.target)

    def _cleanup(self):
        """ Cleanup operations """
        if os.path.exists(self.target) and os.path.ismount(self.target):
            try:
                run(['umount', '-fl', self.target], split=False)
            except (OSError, CalledProcessError) as e:
                api.current_logger().warning('Unmounting %s failed with: %s', self.target, str(e))
        for directory in itertools.chain(self.additional_directories, (self.target,)):
            try:
                run(['rm', '-rf', directory], split=False)
            except (OSError, CalledProcessError) as e:
                api.current_logger().warning('Removing mount directory %s failed with: %s', directory, str(e))

    def mount(self):
        """ Performs the mount if MountConfig.should_create = True """
        if self._config.should_create:
            self._create()

    def _create(self):
        self._cleanup()
        for directory in itertools.chain(self.additional_directories, (self.target,)):
            try:
                _makedirs(directory, exists_ok=True)
            except (OSError) as e:
                raise MountError('Failed to create mount target directory {}'.format(directory), str(e))
        try:
            run(['mount'] + self._mount_options() + [self.target], split=False)
        except (OSError, CalledProcessError) as e:
            api.current_logger().warning('Mounting %s failed with: %s', self.target, str(e), exc_info=True)
            raise MountError(
                message='Mount operation with mode {} from {} to {} failed: {}'.format(
                    self._mode, self.source, self.target, str(e)),
                details=None)
        return self

    def umount(self):
        """ Performs the umount if MountConfig.should_cleanup = True """
        if self._config.should_cleanup:
            self._cleanup()

    def __enter__(self):
        self.mount()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.umount()


class NullMount(MountingBase):
    """ This is basically a NoOp for compatibility with other mount operations, in case a mount is optional """

    def __init__(self, target, config=MountConfig.AttachOnly):
        super(NullMount, self).__init__(source=target, target=target, mode=MountingMode.NONE, config=config)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass


class LoopMount(MountingBase):
    """ Performs loop mounts """

    def __init__(self, source, target, config=MountConfig.Mount):
        super(LoopMount, self).__init__(source=source, target=target, mode=MountingMode.LOOP, config=config)


class BindMount(MountingBase):
    """ Performs bind mounts """

    def __init__(self, source, target, config=MountConfig.Mount):
        super(BindMount, self).__init__(source=source, target=target, mode=MountingMode.BIND, config=config)


class TypedMount(MountingBase):
    """ Performs a typed mounts """

    def __init__(self, fstype, source, target, config=MountConfig.Mount):
        super(TypedMount, self).__init__(source=source, target=target, mode=MountingMode.FSTYPE, config=config)
        self.fstype = fstype

    def _mount_options(self):
        return [
            '-t', self.fstype,
            self.source
        ]


class OverlayMount(MountingBase):
    """ Performs an overlayfs mount """

    def __init__(self, name, source, workdir, config=MountConfig.Mount):
        super(OverlayMount, self).__init__(source=source, target=os.path.join(workdir, name),
                                           mode=MountingMode.OVERLAY, config=config)
        self._upper_dir = os.path.join(workdir, 'upper')
        self._work_dir = os.path.join(workdir, 'work')
        self.additional_directories = (self._upper_dir, self._work_dir)

    def _mount_options(self):
        return [
            '-t', 'overlay', 'overlay2',
            '-o', 'lowerdir={},upperdir={},workdir={}'.format(self.source, self._upper_dir, self._work_dir)
        ]
