#!/bin/bash
# actually perform the upgrade, using UPGRADEBIN (set in /etc/conf.d)

export DRACUT_SYSTEMD=1
if [ -f /dracut-state.sh ]; then
    . /dracut-state.sh 2>/dev/null
fi
type getarg >/dev/null 2>&1 || . /lib/dracut-lib.sh

get_rhel_major_release() {
    local os_version
    os_version=$(grep -o '^VERSION="[0-9][0-9]*\.' /etc/initrd-release | grep -o '[0-9]*')
    [ -z "$os_version" ] && {
        # This should not happen as /etc/initrd-release is supposed to have API
        # stability, but check is better than broken system.
        warn "Cannot determine the major RHEL version."
        warn "The upgrade environment cannot be setup reliably."
        echo "Content of the /etc/initrd-release:"
        cat /etc/initrd-release
        exit 1
    }

    echo "$os_version"
}

RHEL_OS_MAJOR_RELEASE=$(get_rhel_major_release)
export RHEL_OS_MAJOR_RELEASE
export LEAPPBIN=/usr/bin/leapp
export LEAPPHOME=/root/tmp_leapp_py3
export LEAPP3_BIN=$LEAPPHOME/leapp3

export NEWROOT=${NEWROOT:-"/sysroot"}

NSPAWN_OPTS="--capability=all --bind=/dev --bind=/dev/pts --bind=/proc --bind=/run/udev --bind=/run/lock"
[ -d /dev/mapper ] && NSPAWN_OPTS="$NSPAWN_OPTS --bind=/dev/mapper"
if [ "$RHEL_OS_MAJOR_RELEASE" == "8" ]; then
    # IPU 7 -> 8
    NSPAWN_OPTS="$NSPAWN_OPTS --bind=/sys --bind=/run/systemd"
else
    # IPU 8 -> 9
    # TODO(pstodulk, mreznik): Why --console=pipe? Is it ok? Discovered a weird
    # issue on IPU 8 -> 9 without that in our VMs
    NSPAWN_OPTS="$NSPAWN_OPTS --bind=/sys:/hostsys --console=pipe"
    [ -e /sys/firmware/efi/efivars ] && NSPAWN_OPTS="$NSPAWN_OPTS --bind=/sys/firmware/efi/efivars"
fi
export NSPAWN_OPTS="$NSPAWN_OPTS --keep-unit --register=no --timezone=off --resolv-conf=off"


#
# Temp for collecting and preparing tarball
#
LEAPP_DEBUG_TMP="/tmp/leapp-debug-root"

#
# Number of times to emit all chunks
#
# To avoid spammy parts of console log, second and later emissions
# take longer delay in-between.  For example, with N being 3,
# first emission is done immediately, second after 10s, and the
# third one after 20s.
#
IBDMP_ITER=3

#
# Size of one payload chunk
#
# IOW, amount of characters in a single chunk of the base64-encoded
# payload.   (By base64 standard, these characters are inherently ASCII,
# so ie. they correspond to bytes.)
#
IBDMP_CHUNKSIZE=40

collect_and_dump_debug_data() {
    #
    # Collect various debug files and dump tarball using ibdmp
    #
    local tmp=$LEAPP_DEBUG_TMP
    local data=$tmp/data
    mkdir -p "$data" || { echo >&2 "fatal: cannot create leapp dump data dir: $data"; exit 4; }
    journalctl -amo verbose >"$data/journalctl.log"
    mkdir -p "$data/var/lib/leapp"
    mkdir -p "$data/var/log"
    cp -vr "$NEWROOT/var/lib/leapp/leapp.db" \
          "$data/var/lib/leapp"
    cp -vr "$NEWROOT/var/log/leapp" \
          "$data/var/log"
    tar -cJf "$tmp/data.tar.xz" "$data"
    ibdmp "$tmp/data.tar.xz"
    rm -r "$tmp"
}

want_inband_dump() {
    #
    # True if dump collection is needed given leapp exit status $1 and kernel option
    #
    local leapp_es=$1
    local mode
    local kopt
    kopt=$(getarg 'rd.upgrade.inband')
    case $kopt in
        always|never|onerror)   mode="$kopt" ;;
        "")                     mode="never" ;;
        *)  warn "ignoring unknown value of rd.upgrade.inband (dump will be disabled): '$kopt'"
            return 2 ;;
    esac
    case $mode:$leapp_es in
        always:*)   return 0 ;;
        never:*)    return 1 ;;
        onerror:0)  return 1 ;;
        onerror:*)  return 0 ;;
    esac
}

ibdmp() {
    #
    # Dump tarball $1 in base64 to stdout
    #
    # Tarball is encoded in a way that:
    #
    #   * final data can be printed to plain text terminal,
    #   * tarball can be restored by scanning the saved
    #     terminal output,
    #   * corruptions caused by extra terminal noise
    #     (extra lines, extra characters within lines,
    #     line splits..) can be corrected.
    #
    # That is,
    #
    #   1. encode tarball using base64
    #
    #   2. pre-pend line `chunks=CHUNKS,md5=MD5` where
    #      MD5 is the MD5 digest of original tarball and
    #      CHUNKS is number of upcoming Base64 chunks
    #
    #   3. decorate each chunk with prefix `N:` where
    #      N is number of given chunk.
    #
    #   4. Finally print all lines (prepended "header"
    #      line and all chunks) several times, where
    #      every iteration should be prefixed by
    #      `_ibdmp:I/TTL|` and suffixed by `|`.
    #      where `I` is iteration number and `TTL` is
    #      total iteration numbers.
    #
    # Decoder should look for strings like this:
    #
    #     _ibdmp:I/J|CN:PAYLOAD|
    #
    # where I, J and CN are integers and PAYLOAD is a slice of a
    # base64 string.
    #
    # Here, I represents number of iteration, J total of iterations
    # ($IBDMP_ITER), and CN is number of given chunk within this
    # iteration.  CN goes from 1 up to number of chunks (CHUNKS)
    # predicted by header.
    #
    # Each set corresponds to one dump of the tarball and error
    # correction is achieved by merging sets using these rules:
    #
    #    1. each set has to contain header (`chunks=CHUNKS,
    #       md5=MD5`) prevalent header wins.
    #
    #    2. each set has to contain number of chunks
    #       as per header
    #
    #    3. chunks are numbered so they can be compared across
    #       sets; prevalent chunk wins.
    #
    # Finally the merged set of chunks is decoded as base64.
    # Resulting data has to match md5 sum or we're hosed.
    #
    local tarball=$1
    local tmp=$LEAPP_DEBUG_TMP/ibdmp
    local md5
    local i
    mkdir -p "$tmp"
    base64 -w "$IBDMP_CHUNKSIZE" "$tarball" > "$tmp/b64"
    md5=$(md5sum "$tarball" | sed 's/ .*//')
    chunks=$(wc -l <"$tmp/b64")
    (
        set +x
        echo "chunks=$chunks,md5=$md5"
        cnum=1
        while read -r chunk; do
            echo "$cnum:$chunk"
            ((cnum++))
        done <"$tmp/b64"
    ) >"$tmp/report"
    i=0
    while test "$i" -lt "$IBDMP_ITER"; do
        sleep "$((i * 10))"
        ((i++))
        sed "s%^%_ibdmp:$i/$IBDMP_ITER|%; s%$%|%; " <"$tmp/report"
    done
}


do_upgrade() {
    local args="" rv=0
    #FIXME: set here params we would like to possible use...
    #getargbool 0 rd.upgrade.test && args="$args --testing"
    #getargbool 0 rd.upgrade.verbose && args="$args --verbose"
    getargbool 0 rd.upgrade.debug && args="$args --debug"

    # Force selinux into permissive mode unless booted with 'enforcing=1'.
    # FIXME: THIS IS A BIG STUPID HAMMER AND WE SHOULD ACTUALLY SOLVE THE ROOT
    # PROBLEMS RATHER THAN JUST PAPERING OVER THE WHOLE THING. But this is what
    # Anaconda did, and upgrades don't seem to work otherwise, so...
    if [ -f /sys/fs/selinux/enforce ]; then
        enforce=$(< /sys/fs/selinux/enforce)
        getargbool 0 enforcing || echo 0 > /sys/fs/selinux/enforce
    fi

    # and off we go...
    # NOTE: in case we would need to run leapp before pivot, we would need to
    #       specify where the root is, e.g. --root=/sysroot
    # TODO: update: systemd-nspawn
    /usr/bin/systemd-nspawn $NSPAWN_OPTS -D "$NEWROOT" /usr/bin/bash -c "mount -a; $LEAPPBIN upgrade --resume $args"
    rv=$?

    # NOTE: flush the cached content to disk to ensure everything is written
    sync

    #FIXME: for debugging purposes; this will be removed or redefined in future
    getarg 'rd.upgrade.break=leapp-upgrade' 'rd.break=leapp-upgrade' && \
        emergency_shell -n upgrade "Break after LEAPP upgrade stop"

    if [ "$rv" -eq 0 ]; then
        # run leapp to proceed phases after the upgrade with Python3
        #PY_LEAPP_PATH=/usr/lib/python2.7/site-packages/leapp/
        #$NEWROOT/bin/systemd-nspawn $NSPAWN_OPTS -D $NEWROOT -E PYTHONPATH="${PYTHONPATH}:${PY_LEAPP_PATH}" /usr/bin/python3 $LEAPPBIN upgrade --resume $args

        # on aarch64 systems during el8 to el9 upgrades the swap is broken due to change in page size (64K to 4k)
        # adjust the page size before booting into the new system, as it is possible the swap is necessary for to boot
        # `arch` command is not available in the dracut shell, using uname -m instead
        [ "$(uname -m)" = "aarch64" -a "$RHEL_OS_MAJOR_RELEASE" = "9" ] && {
            cp -aS ".leapp_bp" $NEWROOT/etc/fstab /etc/fstab
            # swapon internally uses mkswap and both swapon and mkswap aren't available in dracut shell
            # as a workaround we can use the one from $NEWROOT in $NEWROOT/usr/sbin
            # for swapon to find mkswap we must temporarily adjust the PATH
            # NOTE: we want to continue the upgrade even when the swapon command fails as users can fix it
            # manually later. It's not a major blocker.
            PATH="$PATH:${NEWROOT}/usr/sbin/" swapon -af || echo >&2 "Error: Failed fixing the swap page size. Manual action is required after the upgrade."
            mv /etc/fstab.leapp_bp /etc/fstab
        }

        # NOTE:
        # mount everything from FSTAB before run of the leapp as mount inside
        # the container is not persistent and we need to have mounted /boot
        # all FSTAB partitions. As mount was working before, hopefully will
        # work now as well. Later this should be probably modified as we will
        # need to handle more stuff around storage at all.
        /usr/bin/systemd-nspawn $NSPAWN_OPTS -D "$NEWROOT" /usr/bin/bash -c "mount -a; /usr/bin/python3 $LEAPP3_BIN upgrade --resume $args"
        rv=$?
    fi

    # Dump debug data in case something went wrong
    if want_inband_dump "$rv"; then
        collect_and_dump_debug_data
    fi

    # NOTE: THIS SHOULD BE AGAIN PART OF LEAPP IDEALLY
    ## backup old product id certificates
    #chroot $NEWROOT /bin/sh -c 'mkdir /etc/pki/product_old; mv -f /etc/pki/product/*.pem /etc/pki/product_old/'

    ## install new product id certificates
    #chroot $NEWROOT /bin/sh -c 'mv -f /system-upgrade/*.pem /etc/pki/product/'

    # restore things twiddled by workarounds above. TODO: remove!
    if [ -f /sys/fs/selinux/enforce ]; then
        echo "$enforce" > /sys/fs/selinux/enforce
    fi
    return $rv
}

save_journal() {
    # Q: would it be possible that journal will not be flushed completely yet?
    echo "writing logs to disk and rebooting"

    local logfile="/sysroot/tmp-leapp-upgrade.log"

    # Create logfile if it doesn't exist
    [ -n "$logfile" ] && true > $logfile

    # If file exists save the journal
    if [ -e $logfile ]; then
        # Add a separator
        echo "### LEAPP reboot ###" > $logfile

        # write out the logfile
        journalctl -a -m >> $logfile

        # We need to run the actual saving of leapp-upgrade.log in a container and mount everything before, to be
        # sure /var/log is mounted in case it is on a separate partition.
        local store_cmd="mount -a"
        local store_cmd="$store_cmd; cat /tmp-leapp-upgrade.log >> /var/log/leapp/leapp-upgrade.log"

        /usr/bin/systemd-nspawn $NSPAWN_OPTS -D "$NEWROOT" /usr/bin/bash -c "$store_cmd"

        rm -f $logfile
    fi
}


############################### MAIN #########################################
# get current mount options of $NEWROOT
# FIXME: obviously this is still wrong solution, but resolve that later, OK?
old_opts=""
declare mount_id parent_id major_minor root mount_point options rest
# shellcheck disable=SC2034  # Unused variables left for readability
while read -r mount_id parent_id major_minor root mount_point options \
        rest ; do
    if [ "$mount_point" = "$NEWROOT" ]; then
        old_opts="$options"
        break
    fi
done < /proc/self/mountinfo
if [ -z "$old_opts" ]; then
    old_opts="defaults,ro"
fi

# enable read/write $NEWROOT
mount -o "remount,rw" "$NEWROOT"

##### do the upgrade #######
(
    [ ! -x "$NEWROOT$LEAPPBIN" ] && {
        warn "upgrade binary '$LEAPPBIN' missing!"
        exit 1
    }

    do_upgrade || exit $?
)
result=$?

##### safe the data and remount $NEWROOT as it was previously mounted #####
save_journal

#FIXME: for debugging purposes; this will be removed or redefined in future
getarg 'rd.break=leapp-logs' && emergency_shell -n upgrade "Break after LEAPP save_journal"

# NOTE: flush the cached content to disk to ensure everything is written
sync
mount -o "remount,$old_opts" "$NEWROOT"
exit $result

