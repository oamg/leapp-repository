# Target userspace creator
The very core of a RHEL upgrade process is installing packages of the target
system. When these packages are built, however, they expect that they will
be installed on a target system not on some old RHEL with an old package
manager. Therefore, they can use some of the newer features of RPM such as rich
dependencies, etc. Therefore, attempting to use RHEL7 RPM stack to install RHEL8
RPMs might not work at all.

Therefore, leapp downloads and sets up a very bare-bones installation of the target
system, commonly referred to as _target userspace_. The _Target userspace creator_ is
then the actor responsible performing the entire set up of the userspace. To set up
a minimal target system, one needs access to target repositories, so that the packages
constituting the bare bones system can be downloaded and installed.

## Scratch container
### When we want to modify the source system, but we also don't want to

As introduction foreshadows, we need to modify the source system in order to
achieve access to target repositories. However, modifying key configuration
of the source system such as the repositories defined in `/etc/yum.repos.d`
can be problematic, as the tool doing these temporary modifications needs to
gracefully roll back these changes even in the presence of unforeseen problems.
Speaking plainly, errors in leapp and unforeseen external commands cannot result
in the source system loosing repository access after a failed attempted upgrade.
Therefore, leapp uses an [OverlayFS](https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html)
filesystem with the lower `lowerdir` being source system's `/`. This filesystem
is mounted at `/var/lib/leapp/scratch/mounts/root_/system_overlay`.
If you look at the mount target during certain points in the upgrade,
the path would contain a root file hierarchy as if the `/` of the source system was bind-mounted there.
However, any changes performed by leapp in `/var/lib/leapp/scratch/mounts/root_/system_overlay`,
are not reflected in `/` of the root system, and, instead, they
are written to `/var/lib/leapp/scratch/mounts/root_/upper`. The situation is a
bit more nuanced, since every mounted device of the source filesystem has to
have its own OverlayFS mount, but the principle-use OverlayFS mounts to seemingly
modify source system-remains the same.

To trick various utilities used by leapp to use the (modified) root hierarchy mounted at
`/var/lib/leapp/scratch/mounts/root_/system_overlay` instead of the actual `/`, all external
commands that modify the source `/`, or need to subsequently work with a modified `/` are
executed with a `systemd-nspawn` container. This container, commonly referred to as the _scratch container_,
uses the root filesystem present at `/var/lib/leapp/scratch/mounts/root_/system_overlay`
is used as the root of the container using
the `-D` option.

#### An important detail in how is the Scrach container set up
If we attempt to perform the actual download and installation of the target userspace,
having the scratch container set up as described above, as 
```
dnf install --installroot /var/lib/leapp/elXuserspace dnf
```
we realize there is a problem with the mounting scheme.
Although the command will go through just fine, it will have a
different effect than we expected. Since we are in an overlay, after the command
finishes, there will be no `/var/lib/leapp/elXuserspace` (from the perspective of the host/source system)
since all modifications
are being written to overlay's upper directories. Therefore, we have to perform an
additional bindmount of source system's `/var/lib/leapp/elXuserspace` 
to `/var/lib/leapp/scratch/installroot`. Therefore, if you look at leapp's logs, you will see a slightly
mysterious command that installs target RHEL's dnf into `/installroot`.

#### A comprehensive example of what is mounted where in the scratch container
Consider a source system with the following file system table: 

| Device      | Mounted at |
|--------     |--------    |
| `/dev/vda1` | `/`        |
| `/dev/vda2` | `/boot`    |
| `/dev/vda3` | `/var`     |

Leapp would create the scratch container as follows:

| Source system mountpoint | OverlayFS lower dir | OverlayFS upper dir                             | OverlayFS work dir                             |
|--------------------------|---------------------|---------------------                            |--------------------                            |
| `/`                      | `/`                 | `/var/lib/leapp/scratch/mounts/root_/upper`     | `/var/lib/leapp/scratch/mounts/root_/work`     |
| `/boot`                  | `/boot`             | `/var/lib/leapp/scratch/mounts/root_boot/upper` | `/var/lib/leapp/scratch/mounts/root_boot/work` |
| `/var`                   | `/var`              | `/var/lib/leapp/scratch/mounts/root_var/upper`  | `/var/lib/leapp/scratch/mounts/root_var/work`  |
 
### Target repositories and how are they obtained
> This section is currently under construction

### Broken symbolic links
> This section is currently under construction
