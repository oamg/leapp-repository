#!/bin/bash

# shellcheck disable=SC1091  # The file must be always present to boot the system
type getarg >/dev/null 2>&1 || . /lib/dracut-lib.sh

log_debug() {
    # TODO(pstodulk): The arg is probably not needed
    getarg 'rd.upgrade.debug' && echo >&2 "Upgrade Initqueue Debug: $1"
}


check_reqs_in_dir() {
    log_debug "Check resources from: $1"
    result=0
    # shellcheck disable=SC2045  # Iterating over ls should be fine (there should be no whitespaces)
    for fname in $(ls -1 "$1"); do
        # We grep for What=/dev explicitly to exclude bind mounting units
        resource_path=$(grep "^What=/dev/" "$1/$fname" | cut -d "=" -f2-)
        if [ -z "$resource_path" ]; then
            # Grep found no match, meaning that the unit is mounting something different than a block device
            continue
        fi

        grep -E "^Options=.*bind.*" "$1/$fname" &>/dev/null
        is_bindmount=$?
        if [ $is_bindmount -eq 0 ]; then
            # The unit contains Options=...,bind,..., or Options=...,rbind,... so it is a bind mount -> skip
            continue
        fi

        if [ ! -e "$resource_path" ]; then
            log_debug "Waiting for missing resource: '$resource_path'"
            result=1
        fi
    done

    return $result
}

SYSTEMD_DIR="/usr/lib/systemd/system"
LOCAL_FS_MOUNT_DIR="$SYSTEMD_DIR/local-fs.target.requires"

check_reqs_in_dir "$LOCAL_FS_MOUNT_DIR"
