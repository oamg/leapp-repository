# Leapp data
There are some information essential for Leapp in-place upgrades, that leapp just can't figure out itself or from the source system, such information are provided as files collectively called "Leapp data".
Leapp data files consists of files bundled with the `leapp-upgrade-elXelY` RPM (leapp-repository component) and can be found in `/etc/leapp/files` after installation. These files are:
```{toctree}
:maxdepth: 1
repomap
pes-events
dddd
```
## How often are leapp data files updated?
We update leapp data files basically in every new version of the leapp-repository component - if there are any updates since the last version. So the data in the latest release is usually less then 6months old. Usually we update these files several times during the development cycle when the last update happens usually close to the new upstream release / end of devel freeze to bring in the most up-to-date content.
