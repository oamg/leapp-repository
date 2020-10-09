#!/bin/bash
# actually perform the upgrade, using UPGRADEBIN (set in /etc/conf.d)

export DRACUT_SYSTEMD=1
if [ -f /dracut-state.sh ]; then
    . /dracut-state.sh 2>/dev/null
fi
type getarg >/dev/null 2>&1 || . /lib/dracut-lib.sh

export LEAPPBIN=/usr/bin/leapp
export LEAPPHOME=/root/tmp_leapp_py3
export LEAPP3_BIN=$LEAPPHOME/leapp3

export NEWROOT=${NEWROOT:-"/sysroot"}

NSPAWN_OPTS="--capability=all --bind=/sys --bind=/dev --bind=/dev/pts --bind=/run/systemd --bind=/proc"
[ -d /dev/mapper ] NSPAWN_OPTS="$NSPAWN_OPTS --bind=/dev/mapper"
export NSPAWN_OPTS="$NSPAWN_OPTS --bind=/run/udev --keep-unit --register=no --timezone=off --resolv-conf=off"


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
    /usr/bin/systemd-nspawn $NSPAWN_OPTS -D $NEWROOT /usr/bin/bash -c "mount -a; $LEAPPBIN upgrade --resume $args"
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

        # NOTE:
        # mount everything from FSTAB before run of the leapp as mount inside
        # the container is not persistent and we need to have mounted /boot
        # all FSTAB partitions. As mount was working before, hopefully will
        # work now as well. Later this should be probably modified as we will
        # need to handle more stuff around storage at all.
        /usr/bin/systemd-nspawn $NSPAWN_OPTS -D $NEWROOT /usr/bin/bash -c "mount -a; /usr/bin/python3 $LEAPP3_BIN upgrade --resume $args"
        rv=$?
    fi

    # NOTE: THIS SHOULD BE AGAIN PART OF LEAPP IDEALLY
    ## backup old product id certificates
    #chroot $NEWROOT /bin/sh -c 'mkdir /etc/pki/product_old; mv -f /etc/pki/product/*.pem /etc/pki/product_old/'

    ## install new product id certificates
    #chroot $NEWROOT /bin/sh -c 'mv -f /system-upgrade/*.pem /etc/pki/product/'

    # restore things twiddled by workarounds above. TODO: remove!
    if [ -f /sys/fs/selinux/enforce ]; then
        echo $enforce > /sys/fs/selinux/enforce
    fi
    return $rv
}

save_journal() {
    # Q: would it be possible that journal will not be flushed completely yet?
    echo "writing logs to disk and rebooting"

    local logfile="/sysroot/tmp-leapp-upgrade.log"

    # Create logfile if it doesn't exist
    [ -n $logfile ] && > $logfile

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

        /usr/bin/systemd-nspawn $NSPAWN_OPTS -D $NEWROOT /usr/bin/bash -c "$store_cmd"

        rm -f $logfile
    fi
}


############################### MAIN #########################################
# get current mount options of $NEWROOT
# FIXME: obviously this is still wrong solution, but resolve that later, OK?
old_opts=""
declare mount_id parent_id major_minor root mount_point options rest
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
mount -o "remount,rw" $NEWROOT

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
mount -o "remount,$old_opts" $NEWROOT
exit $result

