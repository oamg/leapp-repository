#!/bin/sh
# -*- mode: shell-script; indent-tabs-mode: nil; sh-basic-offset: 4; -*-
# ex: ts=8 sw=4 sts=4 et filetype=sh

type info >/dev/null 2>&1 || . /lib/dracut-lib.sh

export NEWROOT=${NEWROOT:-"/sysroot"}

filtersubvol() {
    _oldifs="$IFS"
    IFS=","
    set "$@"
    IFS="$_oldifs"
    while [ $# -gt 0 ]; do
        case $1 in
            subvol=*) :;;
            *) printf '%s' "${1}," ;;
        esac
        shift
    done
}

mount_usr()
{
    # check, if we have to mount the /usr filesystem
    while read -r _dev _mp _fs _opts _freq _passno; do
        [ "${_dev%%#*}" != "$_dev" ] && continue
        if [ "$_mp" = "/usr" ]; then
            case "$_dev" in
                LABEL=*)
                    _dev="$(echo "$_dev" | sed 's,/,\\x2f,g')"
                    _dev="/dev/disk/by-label/${_dev#LABEL=}"
                    ;;
                UUID=*)
                    _dev="${_dev#block:}"
                    _dev="/dev/disk/by-uuid/${_dev#UUID=}"
                    ;;
            esac

            # shellcheck disable=SC2154 # Variable root is assigned by dracut
            _root_dev=${root#block:}

            if strstr "$_opts" "subvol=" && \
                [ "$(stat -c '%D:%i' "$_root_dev")" = "$(stat -c '%D:%i' "$_dev")" ] && \
                [ -n "$rflags" ]; then
                # for btrfs subvolumes we have to mount /usr with the same rflags
                rflags=$(filtersubvol "$rflags")
                rflags=${rflags%%,}
                _opts="${_opts:+${_opts},}${rflags}"
            elif getargbool 0 ro; then
                # if "ro" is specified, we want /usr to be mounted read-only
                _opts="${_opts:+${_opts},}ro"
            elif getargbool 0 rw; then
                # if "rw" is specified, we want /usr to be mounted read-write
                _opts="${_opts:+${_opts},}rw"
            fi
            echo "$_dev ${NEWROOT}${_mp} $_fs ${_opts} $_freq $_passno"
            _usr_found="1"
            break
        fi
    done < "${NEWROOT}/etc/fstab" >> /etc/fstab

    if [ "$_usr_found" != "" ]; then
        info "Mounting /usr with -o $_opts"
        mount "${NEWROOT}/usr" 2>&1 | vinfo
        mount -o remount,rw "${NEWROOT}/usr"

        if ! ismounted "${NEWROOT}/usr"; then
            warn "Mounting /usr to ${NEWROOT}/usr failed"
            warn "*** Dropping you to a shell; the system will continue"
            warn "*** when you leave the shell."
            action_on_fail
        fi
    fi
}

if [ -f "${NEWROOT}/etc/fstab" ]; then
    # In case we have the LVM command available try make it activate all partitions
    if command -v lvm 2>/dev/null 1>/dev/null; then
        lvm vgchange -a y
    fi

    mount_usr
fi
