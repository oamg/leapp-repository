**Before doing anything, please read the [leapp-repository documentation](https://leapp-repository.readthedocs.io/).**

Also, you could find the [Leapp framework documentation](https://leapp.readthedocs.io/) useful to read.

---

## Troubleshooting

### Where can I report an issue or RFE related to the framework or other actors?

- GitHub issues are preferred:
  - Leapp framework: [https://github.com/oamg/leapp/issues/new/choose](https://github.com/oamg/leapp/issues/new/choose)
  - Leapp actors: [https://github.com/oamg/leapp-repository/issues/new/choose](https://github.com/oamg/leapp-repository/issues/new/choose)

- When filing an issue, include:
  - Steps to reproduce the issue
  - *All files in /var/log/leapp*
  - */var/lib/leapp/leapp.db*
  - *journalctl*
  - If you want, you can optionally send any other relevant information (e.g. storage, network)

**For your convenience you can pack all logs with this command:**

`# tar -czf leapp-logs.tgz /var/log/leapp /var/lib/leapp/leapp.db`

Then you may attach only the `leapp-logs.tgz` file.

### Where can I seek help?
We’ll gladly answer your questions and lead you to through any troubles with the
actor development.

You can reach us in the [discussions sections of our GitHub repository](https://github.com/oamg/leapp-repository/discussions).
