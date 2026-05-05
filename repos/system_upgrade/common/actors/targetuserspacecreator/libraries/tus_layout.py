"""
On-disk layout, scratch/overlay/nspawn setup, and the developer-only
persistent package cache for the ``targetuserspacecreator`` actor.

:func:`compute` resolves all the paths the actor works with, honouring the
``LEAPP_CONTAINER_ROOT`` environment variable. :func:`scratch_container` is the
context manager that builds the source overlay, enters it as an nspawn scratch
container, and optionally mounts the target ISO into the container root,
guaranteeing that each layer is torn down in reverse order.

This is a leaf module: it imports only shared leapp libraries.
"""

import contextlib
import os

from leapp.libraries.common import mounting, overlaygen
from leapp.libraries.common.config import get_env
from leapp.libraries.common.config.version import get_target_major_version

# Default container root; overridable via LEAPP_CONTAINER_ROOT
_DEFAULT_CONTAINER_ROOT = '/var/lib/leapp'

# Name of the target userspace directory
_USERSPACE_DIRNAME_TEMPLATE = 'el{target_major}userspace'

# Name of the target userspace directory
_INSTALLROOT_DIRNAME_TEMPLATE = 'el{target_major}target'

_PERSISTENT_PKG_CACHE_DIRNAME = 'persistent_package_cache'

_USERSPACE_GPG_KEYS_DIRNAME = 'leapp-trusted-gpg-keys'


class Layout:
    """Value object describing where the actor builds the target userspace."""

    def __init__(
        self,
        container_root,
        userspace_path,
        scratch_dir,
        mounts_dir,
        installroot_overlay_mountpoint,
        persistent_pkg_cache_path,
        userspace_gpg_keys_dir,
    ):
        """
        Initialize the layout value object.

        :param container_root: Root directory under which everything is created.
        :type container_root: str
        :param userspace_path: Path to the target userspace directory.
        :type userspace_path: str
        :param scratch_dir: Path to the scratch directory used for overlays.
        :type scratch_dir: str
        :param mounts_dir: Path to the directory holding overlay mounts.
        :type mounts_dir: str
        :param installroot_overlay_mountpoint: Mountpoint of the install-root overlay.
        :type installroot_overlay_mountpoint: str
        :param persistent_pkg_cache_path: Path to the developer-only persistent package cache.
        :type persistent_pkg_cache_path: str
        :param userspace_gpg_keys_dir: Path to the trusted GPG keys directory inside the target userspace.
        :type userspace_gpg_keys_dir: str
        """
        self.container_root = container_root
        self.userspace_path = userspace_path
        self.scratch_dir = scratch_dir
        self.mounts_dir = mounts_dir
        self.installroot_overlay_mountpoint = installroot_overlay_mountpoint
        self.persistent_pkg_cache_path = persistent_pkg_cache_path
        self.userspace_gpg_keys_dir = userspace_gpg_keys_dir


def compute():
    """
    Resolve the on-disk layout used by the actor.

    Reads the ``LEAPP_CONTAINER_ROOT`` environment variable (falling back to a
    default) and derives all the paths the actor works with from the target
    major version.

    :returns: The resolved layout of paths.
    :rtype: Layout
    """
    container_root = get_env('LEAPP_CONTAINER_ROOT', _DEFAULT_CONTAINER_ROOT)
    target_major = get_target_major_version()

    userspace_dirname = _USERSPACE_DIRNAME_TEMPLATE.format(target_major=target_major)
    userspace_path = os.path.join(container_root, userspace_dirname)
    scratch_dir = os.path.join(container_root, 'scratch')
    mounts_dir = os.path.join(scratch_dir, 'mounts')
    installroot_dirname = _INSTALLROOT_DIRNAME_TEMPLATE.format(target_major=target_major)
    installroot_overlay_mountpoint = os.path.join('/', installroot_dirname)
    persistent_pkg_cache_path = os.path.join(container_root, _PERSISTENT_PKG_CACHE_DIRNAME)
    userspace_gpg_keys_dir = os.path.join('/', _USERSPACE_GPG_KEYS_DIRNAME)

    return Layout(
        container_root=container_root,
        userspace_path=userspace_path,
        scratch_dir=scratch_dir,
        mounts_dir=mounts_dir,
        installroot_overlay_mountpoint=installroot_overlay_mountpoint,
        persistent_pkg_cache_path=persistent_pkg_cache_path,
        userspace_gpg_keys_dir=userspace_gpg_keys_dir
    )


@contextlib.contextmanager
def scratch_container(layout, inputs):
    """
    Build the scratch container and yield an entered nspawn context.

    The layers are nested and each is torn down in reverse order on exit: the
    source overlay is created first, then entered as an nspawn scratch
    container, and finally the target ISO is optionally mounted into the
    container root.

    :param layout: The :class:`Layout` produced by :func:`compute`.
    :type layout: Layout
    :param inputs: The :class:`~.tus_inputdata.InputData` value object.
    :type inputs: tus_inputdata.InputData
    :yields: An entered ``mounting.NspawnActions`` scratch context.

    .. seealso::
        :func:`leapp.libraries.common.overlaygen.create_source_overlay` for
        exceptions raised while building the source overlay.
    """
    scratch_reserve = overlaygen.get_recommended_leapp_free_space(layout.userspace_path)
    with overlaygen.create_source_overlay(
        mounts_dir=layout.mounts_dir,
        scratch_dir=layout.scratch_dir,
        xfs_info=None,  # the parameter is unused in the function
        storage_info=inputs.storage_info,
        scratch_reserve=scratch_reserve,
    ) as overlay:
        # NullMount (a no-op) is returned when no ISO is present, so this is safe
        # to enter unconditionally.
        # NOTE: switched order - is it relevant? I switched it back. it seems
        # however that the order should not be relevant - if so, it can be moved
        # back (the code looked better that way).
        with overlay.nspawn() as scratch:
            with mounting.mount_upgrade_iso_to_root_dir(overlay.target, inputs.target_iso):
                yield scratch
