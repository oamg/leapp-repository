"""
On-disk layout, scratch/overlay/nspawn setup, and the dev-only persistent
package cache for the ``targetuserspacecreator`` actor (§5, §12).

:func:`compute` resolves all the paths the actor works with (honouring
``LEAPP_CONTAINER_ROOT``) and the reserved free space for the overlay.
:func:`scratch_container` is the context manager that builds the source overlay,
optionally mounts the target ISO into the container root, and enters the result
as an nspawn scratch container - guaranteeing reverse-order teardown.

Leaf module: imports only shared leapp libraries and ``tus_constants``.
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


class Layout:
    """Plain value object describing where the actor builds the userspace."""

    def __init__(
        self,
        container_root,
        userspace_path,
        scratch_dir,
        mounts_dir,
        installroot_overlay_mountpoint,
        persistent_pkg_cache_path,
        scratch_reserve,
    ):
        self.container_root = container_root
        self.userspace_path = userspace_path
        self.scratch_dir = scratch_dir
        self.mounts_dir = mounts_dir
        self.installroot_overlay_mountpoint = installroot_overlay_mountpoint
        self.persistent_pkg_cache_path = persistent_pkg_cache_path
        self.scratch_reserve = scratch_reserve


def compute():
    """Resolve the on-disk layout and the recommended overlay free-space reserve."""
    container_root = get_env('LEAPP_CONTAINER_ROOT', _DEFAULT_CONTAINER_ROOT)
    target_major = get_target_major_version()

    userspace_dirname = _USERSPACE_DIRNAME_TEMPLATE.format(target_major=target_major)
    userspace_path = os.path.join(container_root, userspace_dirname)
    scratch_dir = os.path.join(container_root, 'scratch')
    mounts_dir = os.path.join(scratch_dir, 'mounts')
    installroot_dirname = _INSTALLROOT_DIRNAME_TEMPLATE.format(target_major=target_major)
    installroot_overlay_mountpoint = os.path.join('/', installroot_dirname)
    persistent_pkg_cache_path = os.path.join(container_root, _PERSISTENT_PKG_CACHE_DIRNAME)

    scratch_reserve = overlaygen.get_recommended_leapp_free_space(userspace_path)

    return Layout(
        container_root=container_root,
        userspace_path=userspace_path,
        scratch_dir=scratch_dir,
        mounts_dir=mounts_dir,
        installroot_overlay_mountpoint=installroot_overlay_mountpoint,
        persistent_pkg_cache_path=persistent_pkg_cache_path,
        scratch_reserve=scratch_reserve,
    )


@contextlib.contextmanager
def scratch_container(layout, inputs):
    """
    Establish the scratch container and yield an entered nspawn context (§5).

    Nesting (each layer torn down in reverse order on exit):
      source overlay  ->  optional target-ISO mount into the container root
                      ->  nspawn into the overlay.

    :param layout: The :class:`Layout` produced by :func:`compute`.
    :param inputs: The :class:`~.tus_inputdata.InputData` value object.
    :yields: An entered ``mounting.NspawnActions`` scratch context.
    """
    with overlaygen.create_source_overlay(
        mounts_dir=layout.mounts_dir,
        scratch_dir=layout.scratch_dir,
        xfs_info=None,  # the parameter is unused in the function
        storage_info=inputs.storage_info,
        scratch_reserve=layout.scratch_reserve,
    ) as overlay:
        # NullMount (a no-op) is returned when no ISO is present, so this is safe
        # to enter unconditionally.
        # NOTE: switched order - is it relevant? I switched it back. it seems
        # however that the order should not be relevant - if so, it can be moved
        # back (the code looked better that way).
        with overlay.nspawn() as scratch:
            with mounting.mount_upgrade_iso_to_root_dir(overlay.target, inputs.target_iso):
                yield scratch
