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
    #
    # mount_usr [true | false]
    # Expected a "true" value for the last attempt to mount /usr. On the last
    # attempt, in case of failure drop to shell.
    #
    # Return 0 when everything is all right
    # In case of failure and /usr has been detected:
    #   return 2 when $1 is "true" (drop to shell invoked)
    #            (note: possibly it's nonsense, but to be sure..)
    #   return 1 otherwise
    #
    _last_attempt="$1"
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

    if [ "$_usr_found" = "" ]; then
        # nothing to do
        return 0
    fi

    info "Mounting /usr with -o $_opts"
    mount "${NEWROOT}/usr" 2>&1 | vinfo
    mount -o remount,rw "${NEWROOT}/usr"

    if ismounted "${NEWROOT}/usr"; then
        # success!!
        return 0
    fi

    if [ "$_last_attempt" = "true" ]; then
        warn "Mounting /usr to ${NEWROOT}/usr failed"
        warn "*** Dropping you to a shell; the system will continue"
        warn "*** when you leave the shell."
        action_on_fail
        return 2
    fi

    return 1
}


try_to_mount_usr() {
  _last_attempt="$1"
  if [ ! -f "${NEWROOT}/etc/fstab" ]; then
      warn "File ${NEWROOT}/etc/fstab doesn't exist."
      return 1
  fi

  # In case we have the LVM command available try make it activate all partitions
  if command -v lvm 2>/dev/null 1>/dev/null; then
      lvm vgchange --sysinit -a y || {
          warn "Detected problem when tried to activate LVM VG."
          if [ "$_last_attempt" != "true" ]; then
              # this is not last execution, retry
              return 1
          fi
          # NOTE(pstodulk):
          # last execution, so call mount_usr anyway
          # I am not 100% about lvm vgchange exit codes and I am aware of
          # possible warnings, in this last run, let's keep it on mount_usr
          # anyway..
      }
  fi

  mount_usr "$1"
}

_sleep_timeout=15
_last_attempt="false"
for i in 0 1 2 3 4 5 6 7 8 9 10 11; do
    info "Storage initialisation: Attempt $i of 11. Wait $_sleep_timeout seconds."
    sleep $_sleep_timeout
    if [ $i -eq 11 ]; then
        _last_attempt="true"
    fi
    try_to_mount_usr "$_last_attempt" && break

    # something is wrong. In some cases, storage needs more time for the
    # initialisation - especially in case of SAN.

    if [ "$_last_attempt" = "true" ]; then
        warn "The last attempt to initialize storage has not been successful."
        warn "Unknown state of the storage. It is possible that upgrade will be stopped."
        break
    fi

    warn "Failed attempt to initialize the storage. Retry..."
done

