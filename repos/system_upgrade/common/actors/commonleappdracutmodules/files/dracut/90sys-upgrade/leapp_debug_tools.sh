#!/bin/sh
# library containing some useful functions for debugging in initramfs

# mounts the sysroot
leapp_dbg_mount() {
    systemctl start sysroot.mount
    mount -o remount,rw /sysroot
}

# source programs from $NEWROOT, mount if not mounted
leapp_dbg_source() {
    systemctl is-active sysroot.mount --quiet || {
        echo "sysroot not mounted, mounting...";
        leapp_dbg_mount || return 1
    }

    for dir in /bin /sbin; do
        export PATH="$PATH:${NEWROOT}$dir"
    done

    export LD_LIBRARY_PATH=/sysroot/lib64
}

# chroot into $NEWROOT
leapp_dbg_chroot() {
    systemctl is-active sysroot.mount --quiet || {
        echo "sysroot not mounted, mounting...";
        leapp_dbg_mount || return 1
    }

    for dir in /sys /run /proc /dev /dev/pts; do
        mount --bind $dir "$NEWROOT$dir"
    done || {
        echo "Failed to mount some directories" || return 1
    }

    chroot "$NEWROOT" sh -c "mount -a; /bin/bash"
    for dir in /sys /run /proc /dev/pts /dev; do
        umount "$NEWROOT$dir"
    done
}
