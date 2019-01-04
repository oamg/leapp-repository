---
name: Bug report
about: Create a report to help us improve
labels: bug

---

**Actual behavior**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior
1. install '...'
2. setup '....'
3. run '....'
   (when run `leapp`, use always the `--debug` option to provide more data)
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**System information (please complete the following information):**
 - OS and version: (e.g. Fedora 29 or `$ cat /etc/system-release`)
 - `# uname -a`
 - `# rpm -qa "*leapp*"` (or shorthashes of commits in case of manual installation):
```
# rpm -qa "leapp*"
leapp-0.4.0-1.201812151505Z.87a7b74.master.el7_5.noarch
leapp-repository-data-0.4.0-1.201812131256Z.f25d14e.master.el7_5.noarch
leapp-repository-0.4.0-1.201812131256Z.f25d14e.master.el7_5.noarch
```
 - attach (or provide link to) log files if applicable (optional - may contain confidential information):
   - **_/var/log/upgrade.log_**
   - */tmp/leapp-report.txt*
   - `# tar -czf dnf-debug.tgz /tmp/download-debugdata`
   - */var/lib/leapp/leapp.db*
   - *journalctl*
 - anything else you would like to provide (e.g. storage info):

****

**Additional context**
Add any other context about the problem here.

