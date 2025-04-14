# LiveMode

_LiveMode_ is an experimental feature that partially replaces
leapp's custom upgrade environment with a bootable squashfs image of the target
system. Intuitively, this squashfs-based mechanism is similar to using a live
CD (hence the name LiveMode) from which the DNF transaction and other
post-reboot steps will be applied. Such an upgrade environment closely
resembles an ordinary Linux installation, making developing desired
functionality (e.g. supporting network-based storage) much easier.

## Technical details
During an upgrade, prior to rebooting, leapp constructs a minimal target system
container in order to obtain a version of the DNF stack expected by the new
packages installed during the upgrade. After the container is created, the new
DNF stack is used to download packages that will be installed during the
upgrade. Having all necessary packages, leapp checks the RPM transaction to be
performed during the upgrade. Finally, the upgrade environment is created - an
initramfs containing custom dracut modules that ultimately execute leapp very
early in the boot process. Such an upgrade environment guarantees isolation
from other system services as there is essentially only the upgrade process
running. However, the downside of using such an approach is that the bootup
process of the upgrade environment is non-standard, meaning that almost none of
the classical system initialisation services (e.g., LVM autoactivation) are
running. Developing advanced features such as support for network-based
storage, is, therefore demanding as only a little of the usual initialisation
is present and executed during bootup.

The LiveMode feature obtains a similar isolation level of the upgrade process
in a different way. Instead of using an initramfs image that executes leapp
early, the system boots into a read-only squashfs system built from the target
system container build previously to check the upgrade RPM transaction. Since
leapp controls the creation of the target system container, it is also in
control of what will be running alongside the upgrade process, limiting the
possibility of arbitrary user-defined services interfering with the upgrade.
The upgrade environment boots into the `multi-user.target` target and leapp is
started as an ordinary systemd service. However, the squashfs image needs to be
stored on the disk, and, hence, the using feature **requires about 700mb of
additional disk space**.

## Using the feature
It is possible to use the LiveMode feature by having set `LEAPP_UNSUPPORTED=1`
and running leapp as `leapp upgrade --enable-experimental-feature livemode`.
```
LEAPP_UNSUPPORTED=1 leapp upgrade --enable-experimental-feature livemode
```
### Configuration
The feature offers an extensive list of configuration options that can be set
by creating a YAML file in `/etc/leapp/actor_conf.d/` with the extension
`.yaml`. The content of the configuration file must be a mapping defining the
`livemode` key with a value that is a mapping with (some) of the following
keys:

| Configuration field | Value type | Default | Semantics |
|---------------------|------------|---------|-----------|
| `squashfs_image_path` | `str` | `/var/lib/leapp/live-upgrade.img` |  Location where the squashfs image of the minimal target system will be placed. |
| `additional_packages` | `List[str]` | `[]` | Additional packages to be installed into the squashfs image. |
| `autostart_upgrade_after_reboot` | `bool` | `True` | If set to True, the upgrade will start automatically after the reboot. Otherwise a manual trigger is required. |
| `setup_network_manager` | `bool` | `False` | Try enabling Network Manager in the squashfs image. |
| `dracut_network` | `str` | `''` | Dracut network arguments, required if the `url_to_load_squashfs_from` option is set. |
| `url_to_load_squashfs_image_from` | `str` | `''` | URL pointing to the squashfs image that should be used for the upgrade environment. |
| `setup_passwordless_root` | `bool` | `False` |  If set to True, the root account of the squashfs image will have empty password. Use with caution. |
| `setup_opensshd_using_auth_keys` | `str` | `''` | If set to a non-empty string, openssh daemon will be setup within the squashfs image using the provided authorized keys file. |
| `capture_strace_info_into` | `str` | `''` | If set to a non-empty string, leapp will be executed under strace and results will be stored within the provided file path. |

#### Configuration example
Consider the file `/etc/leapp/actor_conf.d/livemode.yaml` with the following contents.
```
livemode:
  additional_packages : [ vim ]
  autostart_upgrade_after_reboot : false
  setup_network_manager : true
  setup_opensshd_using_auth_keys : /root/.ssh/authorized_keys
```

The configuration results in the following actions:
- Leapp will install the `vim` package into the upgrade environment.
- The upgrade will not be started automatically after reboot. Instead, user
  needs to resume the upgrade manually. Therefore, it is possible to manually
  inspect the system and verify that everything is in order, e.g., all of the
  necessary storage is mounted.
- Leapp will attempt to enable `NetworkManager` inside the upgrade environment
  using source system's network profiles. This attempt is best-effort, meaning
  that there is no guarantee that the network will be functional.
- Leapp will enable the `opensshd` service. If a network access is established
  successfully, it will be possible to login using ssh into the upgrade
  environment using the `root` account and interact with the system.
