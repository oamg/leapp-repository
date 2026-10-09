# targetuserspacecreator — Behavioural Contract

**What this document is.** A specification of the *outside-observable behaviour* of the
`targetuserspacecreator` actor: the messages it consumes and produces, the reports/inhibitors it
raises, the on-disk/container state it guarantees, and the toggles that vary that behaviour. Internal
function and module names are deliberately absent — this is the document a fresh author could be
handed to write the actor's code from scratch, and the yardstick against which a redesign is judged.

**The rule this redesign is measured by.** Behaviour is the contract; the *shape* of the code is not.
A redesign is correct iff every guarantee below still holds. "The new code looks like the old code"
is not a goal and not a gate. Exact report strings, keys, and command flags are pinned by the
behaviour-anchored test suite; where this document says "preserve the baseline text", the tests are
the byte-level source of truth.

**Provenance.** Derived from a code-level read of the baseline actor at `827d1b04` — its consumed and
produced messages, the five inhibitors, the dnf install/failure paths, and the RHUI R1–R7 invariants —
re-expressed here as behaviour. Items that this redesign *intentionally changes* at the interface are
called out in §14 so verification knows they are gone by design, not lost.

Certainty tags: [High] = read directly from source; [Medium]/[Low] = inferred, verify against
baseline during implementation.

---

## 1. Purpose & placement

Build the **target userspace**: a minimal install of the *target* OS RPM stack (dnf, rpm,
util-linux, …) laid into `/var/lib/leapp/el{TARGET_MAJOR}userspace`, so leapp can enter it as a
container (systemd-nspawn / chroot) and run target binaries — the real DNF upgrade transaction and
the dracut initramfs build — as if already on the target OS. The build happens inside a writable
**source overlay** (overlayfs over the running system) entered via nspawn, then is decoupled into its
own directory. [High]

Runs in the **TargetTransactionFacts** phase (tags `IPUWorkflowTag`,
`TargetTransactionFactsPhaseTag`). Effective in-phase order: `createisorepofile` (produces
`CustomTargetRepositoryFile`) → **this actor** → `swapdistropackagesworkaround` (consumes this
actor's output). [High]

---

## 2. Inputs consumed & validation rules

**Consumed messages** [High]:
- `StorageInfo` — **required**. Absence is a hard error (see below).
- `TargetRepositories` — the repos requested for the upgrade (distro + custom).
- `CustomTargetRepositoryFile` — custom `.repo` files to install into the container.
- `RHSMInfo` — subscription-manager facts (present iff the system uses RHSM).
- `RHUIInfo` — cloud RHUI facts; **presence alone switches on the entire RHUI path** (§6, §13).
- `TargetOSInstallationImage` — optional; when present, its ISO is mounted into the container root.
- `TargetUserSpacePreupgradeTasks` — extra packages to install and files to copy into the userspace.
- `XFSPresence` — XFS/ftype facts, threaded into overlay creation.
- `RepositoriesFacts`, `PkgManagerInfo` — consumed **only** on the dnf-failure diagnostic path (§10);
  not read on the success path.

**Validation / hard-stop rules** [High] — each must still fire with equivalent user-facing meaning:
1. No `RHSMInfo` **and** RHSM is not being skipped → stop with a "is this system registered?"-class
   error.
2. RHSM is being skipped **but** `RHSMInfo` is present → stop with an inconsistent-input error.
3. No `StorageInfo` → stop with an error.

("RHSM is being skipped" = the shared `rhsm.skip_rhsm()` predicate, driven by `LEAPP_NO_RHSM` /
`--no-rhsm`.)

**Default packages** always installed into the userspace [High]: `dnf`,
`dnf-command(config-manager)`, `dnf-command(download)`, `util-linux`; plus `install_rpms` from
`TargetUserSpacePreupgradeTasks`. `copy_files` from that message are de-duplicated by (source,
destination) before use.

---

## 3. Outputs produced & their consumers

**Produced messages** [High]:
- `TargetUserSpaceInfo` — the primary output: `path` / `scratch` / `mounts` of the built userspace.
  Consumed by 15+ downstream actors (all dnf transaction/download actors, initramfs generators,
  `adjustlocalrepos`, convert workaround, …). **Any consumer needing the container's *current*
  on-disk repo state reads it from `TargetUserSpaceInfo.path`, not from the snapshot below.**
- `UsedTargetRepositories` — the repoids actually selected/usable. Consumed by 9+ actors
  (dnf actors, `enablerhsmtargetrepos`, `missinggpgkeysinhibitor`, `adjustlocalrepos`, …).
- The **target-repositories snapshot** message (§14 records the model rename) — a point-in-time
  snapshot of the `.repo` files parsed from the build (scratch) container after the target userspace
  has been created. Consumed by **exactly two** actors, both in the later `TargetTransactionChecks`
  phase: `adjustlocalrepos` (reads each repofile's `file`, `repoid`, `baseurl`, `mirrorlist`) and
  `missinggpgkeysinhibitor` (reads `repoid` and the gpg-key fields).
- `Report` — inhibitors/warnings (§8).

**Snapshot-message rationale (the "justify" in keep-rename-justify).** [Facts High; rationale Medium]
- The producer parses the build container's `.repo` files once and ships the parsed result as a
  message. Both consumers run later in `TargetTransactionChecks`; the message lets each obtain the
  target repo metadata (file, repoid, baseurl, mirrorlist, gpg-key fields) without re-implementing
  repofile discovery/parsing, and decouples them from each other and from this actor's internals.
- It is a **produced** message, so leapp persists it — a durable record of the freshly-built
  container's repo state, useful for diagnostics/sosreports.
- It carries the **target** container's repos; keeping it a **distinct type** from the source-system
  `RepositoriesFacts` (same field shape, different subject and lifecycle) prevents the two being
  conflated.
- Staleness is not a hazard: the only later writer of these repofiles is `adjustlocalrepos`, and it
  rewrites only the `baseurl`/`mirrorlist` of local (`file://`) repos, re-reading the on-disk file for
  the actual edit; `missinggpgkeysinhibitor` reads only `repoid`/gpg-key fields, which no consumer
  rewrites.
- **What the rename does NOT change:** same producer, same two consumers, same fields, same timing

---

## 4. Ordering guarantees (other actors may depend on these)

Within a single run of `perform()` the observable sequence is [High]:
1. Consume + validate inputs (§2).
2. Establish the scratch container: reserve space, create source overlay, enter via nspawn, mount the
   target ISO if provided.
3. Establish content access inside scratch: **RHUI client swap first** (if `RHUIInfo`), then RHSM
   container-mode + product-cert switch, CentOS `$stream` variable, install custom repofiles.
4. Discover + select target repositories; raise any repo inhibitor here.
5. Build the target userspace (dnf install into the installroot; cert/repo access; copy files; install
   the leapp dnf plugin; RHUI post-build repofile cleanup; set RHSM container mode).
6. Parse the **build (scratch) container's** repofiles and **produce** the three messages.

The three produced messages are emitted only after a successful build. Any hard-stop raised earlier
(input validation, missing cert, repo inhibitors, RHUI/dnf failures) means no output messages.

---

## 5. Scratch / overlay / nspawn / ISO setup

- Compute the reserved free space for the overlay via the shared overlay helper
  (`overlaygen.get_recommended_leapp_free_space`). [High]
- Create the source overlay (`overlaygen.create_source_overlay`) passing `StorageInfo`, XFS info, and
  the computed scratch reserve; enter it as an nspawn scratch container. [High]
- If a `TargetOSInstallationImage` is present, mount its ISO into the container root
  (`mounting.mount_upgrade_iso_to_root_dir`). This path is **not** covered by the unit suite — treat
  as review-verified. [High]

---

## 6. Content-access establishment (scratch container)

Performed so that `dnf` inside scratch can see the target repos. Order matters (§4 step 3). [High]

1. **RHUI (cloud) client swap** — only if `RHUIInfo` is consumed. Full behaviour is the R1–R7
   acceptance gate in §13. In one line: swap the source RHUI client rpm(s) for the target client
   rpm(s) inside scratch (via `dnf shell`), apply pre/post-install file tasks, and leave
   `/etc/yum.repos.d` consistent — honouring the `bootstrap_target_client` and
   `enable_only_repoids_in_copied_files` toggles that arrive on the message.
2. **RHSM** — set subscription-manager container mode, then switch to the target product certificate.
   The product-cert path is determined by the shared `rhsm.switch_certificate` (auto-discovery with a
   major-version fallback); this actor does **not** compute cert paths itself (§14). A genuine missing
   cert raises the missing-cert inhibitor (§8).
3. **CentOS Stream `$stream` variable** — only when the target distro is CentOS: write
   `{target_major}-stream` into the dnf `$stream` var so stream repo URLs resolve.
4. **Install custom repofiles** — lay each `CustomTargetRepositoryFile` into the container.

---

## 7. Repository discovery & selection

- Discover the repoids provided by the distro (RHSM/RHUI/conversion-aware) and, for cloud, the repoids
  the RHUI clients expose (§13 R2), plus the full set of available repoids in the container. [High]
- Select the usable target repos: match the requested **distro** repos against discovered repoids, and
  the requested **custom** repos against all available repoids. The selected repoids become
  `UsedTargetRepositories` and drive the dnf install (§10). [High]
- **Base-repo (baseos + appstream) presence check** runs by default and is intentionally **skipped**
  in exactly these cases [High]: (a) conversions; (b) source CentOS Stream 8 (CS8→CS9, whose repofile
  layout carries no distro base repoids); (c) a **RHEL target with RHSM skipped** (`--no-rhsm` /
  `LEAPP_NO_RHSM`). Equivalently, it runs when: not a conversion, source is not CS8, and the target is
  either non-RHEL **or** RHEL-with-RHSM-active. (Confirmed by `test__get_distro_available_repoids_
  norhsm_norhui`, which returns an empty set with no inhibitor for RHEL + `skip_rhsm`.)

---

## 8. Inhibitors / reports (all five must survive, with equivalent trigger/severity/semantics)

Exact titles, severities, groups, keys, and remediation text are pinned by the test suite; other
actors (e.g. `missinggpgkeysinhibitor`) may key off them, so preserve them. [High]

| # | Report | Severity | Trigger |
|---|---|---|---|
| 1 | Missing target product certificate | HIGH, inhibitor | `rhsm.switch_certificate` reports no cert for this arch×product-type (genuine miss). Includes a beta-specific note and the `LEAPP_DEVEL_TARGET_RELEASE` remediation; then soft-stops. |
| 2 | Duplicate repositories | MEDIUM, inhibitor | duplicate repoids found — **only when RHSM is being skipped**. |
| 3 | Missing base repositories (baseos/appstream) | HIGH, inhibitor | base repos absent, and not in a §7 skip case. |
| 4 | No enabled target repositories | HIGH, inhibitor | selection yields no usable repos. |
| 5 | Missing custom target repositories | HIGH, inhibitor | a requested custom repo is not available. |

The missing-cert report (1) is generated by the actor catching the shared
`rhsm.MissingTargetProductCertificate` exception and translating it into the report + soft stop — path
determination lives in `rhsm`, the user-facing report lives here (§14). [High]

---

## 9. Userspace build

Observable guarantees of the build [High]:
- The userspace directory is wiped and recreated, then bind-mounted into the scratch container.
- Target GPG keys are imported into the installroot **unless** GPG checking is disabled (§12).
- `dnf install` runs into `--installroot` with the selected repos (§10).
- Repository/certificate access is prepared inside the userspace (§11).
- `copy_files` (from `TargetUserSpacePreupgradeTasks`, de-duplicated) are copied in.
- The leapp DNF plugin is installed into the userspace (`dnflibs.dnfplugin.install`).
- For cloud: RHUI post-build repofile cleanup runs (§13 R6/R7).
- The userspace is (re-)entered via nspawn and subscription-manager container mode is set.

---

## 10. dnf install command + failure diagnosis

**Command shape** [High for presence, Medium for exact flag spelling — pin via tests]: install the
selected packages into `--installroot` with the target `releasever`,
`module_platform_id=platform:el{target_major}`, cache retention (`keepcache`), all repos disabled and
only the selected repoids enabled, `--disableplugin subscription-manager` when RHSM is being skipped,
and `--nogpgcheck` when GPG checking is disabled (§12).

**Failure diagnosis** — on the dnf `CalledProcessError`, exactly these four hints must still be
produced from the same signals [High]:
1. **Disk space** — parse the "more space needed on the … filesystem" text from dnf's output and raise
   a friendly out-of-space error linking the dedicated-`/var/lib/leapp`-partition KB article.
2. **Proxy configured in `dnf.conf`** — detected via `PkgManagerInfo`; hint that leapp is unsupported
   behind a proxy configured that way.
3. **Proxy configured in a `.repo`** — detected via `RepositoriesFacts`; the corresponding proxy hint.
4. **CentOS → RHEL target not released** — hint to pass `LEAPP_DEVEL_TARGET_RELEASE` /
   `--target-version` (the target may not be released yet).

`RepositoriesFacts` and `PkgManagerInfo` are consumed **only** to build hints 2–4.

---

## 11. Certificate / repository-file access

Prepared inside the built userspace [High]:
- Copy certificates into the userspace, **decoupling symlinks** and preserving RPM-owned files under
  `/etc/pki` (see carve-out below), then refresh the CA trust store (`update-ca-trust` via chroot).
- Copy `/etc/rhsm` into the userspace **unless** RHSM is being skipped.
- Shuffle `/etc/yum.repos.d` so the container's repo files are the intended ones, **preserving
  RPM-owned `.repo` files**.

**RPM-ownership rule** [High]: throughout cert/repo handling, files owned by an installed RPM always
win over copied/injected files. RPM-ownership queries skip `/directory-hash` (an EL9+ ca-certificates
performance concern).

> ### CARVE-OUT (frozen — do not redesign)
> The `/etc/pki` symlink-decoupling engine — copy links pointing outside the source dir as real
> files, preserve links pointing inside, skip broken/circular symlinks, RPM-owned files win — is
> **frozen byte-identical** by user instruction. It is the most heavily unit-tested behaviour in the
> actor (~55 cases). Only its *surrounding* call sites may be restructured; its bodies may not.
>
> **Known bug, intentionally NOT fixed here** [High]: the certificate-copy step's broken-symlink
> recovery has a loop that never advances the symlink cursor (it re-reads the *original* link each
> iteration), so a multi-hop RPM-owned symlink chain under `/etc/pki` is misclassified as broken and
> skipped. This is captured by an `xfail` characterization test; fixing it is out of scope for this
> redesign (tracked separately).

---

## 12. Environment-variable switches

Read and honoured [High]:
- `LEAPP_CONTAINER_ROOT` — container root override.
- `LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE` — move the dnf package cache in/out of the userspace's
  `var/cache/dnf` across runs (dev speed-up).
- `LEAPP_NO_RHSM` — drives `rhsm.skip_rhsm()` (skip subscription-manager, disable its dnf plugin, skip
  `/etc/rhsm` copy).
- `LEAPP_NOGPGCHECK` — disable GPG checking (skip key import, add `--nogpgcheck`).
- Target/product-type devel overrides (`LEAPP_DEVEL_TARGET_RELEASE`, product-type overrides).

Removed at the interface (§14): `LEAPP_DEVEL_SKIP_RHSM` (superseded by `LEAPP_NO_RHSM`),
`LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE` (already retired upstream).

---

## 13. RHUI invariants (R1–R7) — cloud client-swap acceptance gate

The RHUI path runs **only** when a `RHUIInfo` message is consumed; falsy → the entire path is a
no-op. Two toggles arrive on `RHUIInfo.target_client_setup_info`:
`enable_only_repoids_in_copied_files` (default true; never overridden upstream, but both branches are
kept) and `bootstrap_target_client` (default true; set false by `cloud/checkrhui` for AWS RHEL8
target, AWS 9→10+ target, and the config-file/custom-RHUI path). Each invariant below is an
observable outcome that must still hold. [High]

- **R1 — copy-target path resolution.** For an RHUI copy task: if the destination resolves to an
  existing directory, the file lands at `destination/basename(source)`; otherwise the destination path
  is used unchanged. Identical semantics at every call site.
- **R2 — client-repoid discovery leaves `/etc/yum.repos.d` byte-identical.** Discovery hides "foreign"
  repofiles (all `*.repo` minus client-owned minus setup-copied), runs `dnf repolist` with only
  client+setup repos visible (source/`-source-`/`-debug-` excluded), and **restores every hidden file
  whether the repolist succeeds or fails**. Net on-disk change: none. A repolist failure is a hard
  stop ("Failed to retrieve repoids provided by target RHUI clients"). When `bootstrap_target_client`
  is false, no files are treated as client-owned.
- **R3 — pre-install tasks (into scratch).** When present: removals first, then host→container copies
  (with parent dirs created). End state: listed files removed, all copies present at destination.
- **R4 — post-install tasks (inside container).** When present: in-container copies to each
  destination (with parent dirs). Applied only after a successful swap.
- **R5 — orchestration order.** Guard on `RHUIInfo`; create userspace dirs (OSError → hard stop);
  pre-install tasks; **if `bootstrap_target_client` is false, return early after pre-install** (no
  swap, no post-install, no cleanup). Otherwise: if `enable_only_repoids_in_copied_files` and
  pre-install tasks exist, restrict the swap to the repoids parsed from the copied `.repo` files (parse
  failure → hard stop "Failed to parse repositories for RHUI"); run the **client swap** via `dnf shell`
  (transaction: remove source clients → install target clients → run) carrying
  `module_platform_id=platform:el{major}`, cache retention, target `releasever`, and
  `--disableplugin subscription-manager` (swap failure → hard stop "Failed to swap RHUI clients to
  establish content access"); apply post-install tasks; look up installed client files (not found →
  hard stop "Could not find the RHEL {major} RHUI client rpm(s)…"); remove injected setup files whose
  container destination is not client-owned and whose source is not in
  `files_supporting_client_operation`.
- **R6 — post-build injected-repofile cleanup.** After the userspace build, for each injected copy that
  is an existing `.repo` file: keep it if an RPM owns it, delete it if none does (prevents duplicate
  repoids in the built userspace).
- **R7 — cleanup placement.** The R6 cleanup runs only for cloud, only when `bootstrap_target_client`
  is false, after the leapp dnf plugin is installed and before subscription-manager container mode is
  set.

**Cross-cutting:** no RHUI action when `RHUIInfo` is falsy; R2 always brackets the repolist with a
guaranteed restore; the swap order is remove → install → run with the four flags above; every RHUI
failure surfaces as a hard stop — never a silent continue.

---
