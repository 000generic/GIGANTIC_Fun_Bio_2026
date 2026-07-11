<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26
Human:   Eric Edsinger
Purpose: Single AI guide for the GIGANTIC data server — covers server
         operation (start, stop, restart, troubleshoot) AND the publishing
         workflow (how a subproject's outputs reach the server). Merges the
         previous AI_GUIDE-server.md and AI_GUIDE-publishing.md per
         gigantic_conventions §3 (one AI_GUIDE per directory; no suffixes).
Scope:   gigantic_project-COPYME/server/ — the GIGANTIC data server and
         everything related to its operation and to publishing subproject
         outputs to it.
History:
  2026-05-26  Consolidated AI_GUIDE-server.md + AI_GUIDE-publishing.md into
              one AI_GUIDE.md. Corrected stale architecture text (server
              reads upload_to_server/ symlinks directly; there is no
              server_data/ hard-copy directory). Updated for the unified
              RUN-start_server.sh driver per §29. Dropped duplicate
              "Honesty about mistakes" section (now in AI_BEHAVIOR.md).
              Added the post-start "SSH tunnel + URL in chat" directive.
============================================================================ -->

# `server/` — AI Guide (server operation + publishing workflow)

This is the single AI guide for the GIGANTIC data server. It covers both
**server operation** (start, stop, restart, troubleshoot, change config)
and the **publishing workflow** (how a subproject's pipeline outputs reach
the server).

For project-wide AI orientation, read `../AI_GUIDE.md` first. For
canonical project conventions, see `../ai/ai_FYIs/gigantic_conventions.md`.

## Documents in this directory

These are the relevant server documents — read them alongside this guide.

| Document | What it covers |
|---|---|
| [`README.md`](README.md) | User-facing quick start: start the server, publish data, reach it from a browser. |
| [`Login-node-server-GUIDE.md`](Login-node-server-GUIDE.md) | **The live deployment.** How the server is run in `local` mode, detached, on `login7` for shared lab access, and **how to restart it safely** — including the `[g]` bracket-trick for stopping it. **Read this before restarting the live server** (see the callout in [Operation → Restart](#restart-the-server)). |
| [`EXCEL_CONVERSION-GUIDE.md`](EXCEL_CONVERSION-GUIDE.md) | The on-the-fly TSV/CSV → `.xlsx` conversion offered in the web UI (refuse-and-report behavior). |
| [`START_HERE-server_config.yaml`](START_HERE-server_config.yaml) | All server configuration (execution_mode, port, `subproject_order` allowlist, `slurm.*`). |
| [`ai/gigantic_server.py`](ai/gigantic_server.py) | Server implementation (stdlib-only; the `ThreadingTCPServer` fix is a hard requirement — see the Login-node guide). |
| [`ai/update_upload_to_server.py`](ai/update_upload_to_server.py) | Shared publisher helper invoked by each subproject's `RUN-update_upload_to_server.sh`. |
| `../AI_GUIDE.md` · `../ai/ai_FYIs/gigantic_conventions.md` | Project-wide AI orientation and canonical conventions. |

| You need... | Section / Document |
|---|---|
| What the server is + architecture | [Architecture](#architecture) |
| Start / stop / restart the server | [Operation](#operation) |
| **Restart the LIVE (login-node) server safely** | [`Login-node-server-GUIDE.md`](Login-node-server-GUIDE.md) |
| Post-start UX: SSH tunnel + URL in chat | [Post-start: tell the user how to reach the server](#post-start-tell-the-user-how-to-reach-the-server) |
| Diagnose a problem | [Troubleshooting](#troubleshooting) |
| Publish a subproject's outputs to the server | [Publishing workflow](#publishing-workflow) |
| Add a new subproject to the served set | [Adding a new subproject to the server](#adding-a-new-subproject-to-the-server) |
| Server config reference | [Configuration parsing](#configuration-parsing) |
| On-the-fly Excel (.xlsx) conversion | [`EXCEL_CONVERSION-GUIDE.md`](EXCEL_CONVERSION-GUIDE.md) |

---

## Architecture

The GIGANTIC data server provides HTTP access to selected pipeline outputs
for collaborators. It is a long-running Python service that reads files
from each subproject's `upload_to_server/` directory.

**Critical: the server reads symlinks, not copies.** There is no
`server_data/` directory and no copying or syncing step. Each subproject's
`upload_to_server/` contains symlinks that point into that subproject's
`OUTPUT_pipeline/` of the canonical `workflow-RUN_N-*` directory. The
server follows those symlinks transparently.

### Data flow (3 steps)

```
Workflow outputs (OUTPUT_pipeline/) inside workflow-RUN_N-*
        |
        | step 1: subproject's RUN-update_upload_to_server.sh
        v
upload_to_server/<unit>/STEP_*/workflow-RUN_*/N-output/<file>  (symlinks)
        |
        | step 2: gigantic_server.py follows the symlinks at HTTP request time
        v
Web browser
```

The server auto-refreshes its file listing every `refresh_interval_seconds`
(default 300s). New publishes appear without restart.

### Key files in this directory

| File | User edits? | Purpose |
|---|---|---|
| `START_HERE-server_config.yaml` | Yes | All server configuration (execution_mode, port, subproject_order, slurm.*) |
| `RUN-start_server.sh` | No | Unified driver — runs locally OR self-submits to SLURM based on execution_mode in the YAML (per §29) |
| `ai/gigantic_server.py` | No | Server implementation (Python; built-in YAML parser; no PyYAML dependency) |
| `ai/update_upload_to_server.py` | No | Shared helper invoked by each subproject's `RUN-update_upload_to_server.sh` |
| `ai/static/icons/` | No | UI icons |
| `logs/` | No | SLURM logs + sbatch wrappers (gitignored via `server/.gitignore`) |

---

## Operation

### Start the server

```bash
bash RUN-start_server.sh
```

The script reads `execution_mode` from `START_HERE-server_config.yaml`:

- `execution_mode: "local"` → runs the server in the foreground of the
  current shell
- `execution_mode: "slurm"` → generates a one-shot sbatch wrapper in
  `logs/` and submits it; returns immediately

Override at the command line for one-off runs:
```bash
bash RUN-start_server.sh --execution slurm    # force slurm
bash RUN-start_server.sh --execution local    # force local
bash RUN-start_server.sh --port 8888          # override port (local mode only)
```

There is **no** separate `RUN-start_server.sbatch`. Per §29, the unified
`RUN-start_server.sh` is the canonical entry point and the only script
the user invokes.

### Stop the server

- **Local mode**: `Ctrl+C` in the running shell
- **SLURM mode**: `scancel <job-id>` (find it with `squeue -u $USER | grep gigantic`)

### Restart the server

> **⚠️ The live deployment runs in `local` mode, detached, on `login7` (not
> SLURM).** To restart THAT server, follow
> [`Login-node-server-GUIDE.md`](Login-node-server-GUIDE.md) exactly —
> especially the `[g]` bracket-trick for stopping it. A plain
> `pkill -f gigantic_server.py` (or `pgrep -f ...`) run over ssh also matches
> the ssh shell executing the command and kills it, so the old server dies, the
> restart step never runs, and no logfile is even created (silent outage). The
> generic stop/start below describes a foreground or SLURM server, not the
> login-node deployment.

Stop, then `bash RUN-start_server.sh` again. Restart is only needed for:

- Port change
- Subproject ordering change in `subproject_order`
- Other server config changes (refresh_interval, display_names,
  exclude_file_patterns)
- Code change to `gigantic_server.py`

For **new published data** (subproject just ran `RUN-update_upload_to_server.sh`),
do **not** restart — the server auto-refreshes within
`refresh_interval_seconds`.

---

## Post-start: tell the user how to reach the server

**After every start or restart, give the user a copy-pasteable way to
reach the server in the same chat message.** Two cases:

### Case 1: server runs on the user's local machine (no tunneling)

Print the URL:

```
http://localhost:9456/
```

(Substitute the actual port from `port:` in the YAML config.)

### Case 2: server runs on a remote / compute node (tunneling required)

This is the common case for SLURM mode on HPC clusters. The user needs
an SSH tunnel from their laptop to the compute node. Construct the
command from what you know about the environment:

1. **The compute node hostname** — for SLURM jobs, read it from the
   SLURM log (`logs/slurm_server_<jobid>.log` line starting with
   `Node:`) or from `squeue -u $USER -j <jobid> -o "%N"`.
2. **The login host** — e.g., `hpg.rc.ufl.edu` for UF HiPerGator. Ask
   the user if you don't already know.
3. **The user's login name** — the user knows this; insert their
   username or a clearly-marked placeholder.
4. **The port** — from `port:` in the YAML config.

Then write the SSH command + URL in chat:

```
ssh -L 9456:c0700a-s2:9456 YOURLOGIN@hpg.rc.ufl.edu
http://localhost:9456/
```

If you cannot determine the compute node yet (job is still queued), tell
the user, and offer to construct the tunnel command once the job starts.

This is a small but important UX detail — without it, the user has to
hunt through SLURM logs themselves.

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `Config file not found` | Wrong working directory | Run from `server/` directory |
| `Subprojects directory does not exist` | Wrong --subprojects-dir | Check the layout; `RUN-start_server.sh` should resolve this automatically |
| Empty landing page | No subprojects with published data; subprojects haven't run their `RUN-update_upload_to_server.sh` | Have each desired subproject run its publisher; wait `refresh_interval_seconds` |
| `Address already in use` | Port conflict | Edit `port:` in YAML or `--port 8888` for one-off |
| Files not updating after publish | Server cache TTL not yet elapsed | Wait `refresh_interval_seconds` (default 300s); only restart if YAML changed |
| Subproject not appearing on landing page | Empty `upload_to_server/`, or subproject not in `subproject_order` allowlist | Run the subproject's publisher; verify the YAML's `subproject_order` includes it |
| SLURM job dies after time limit | Walltime too short | Increase `slurm.time_hours` in YAML; re-submit |
| `slurm.account is unset or still the placeholder` | Default YAML never edited | Edit `slurm.account` and `slurm.qos` in `START_HERE-server_config.yaml` |
| Symlink shows broken | Underlying workflow output moved/deleted | Re-run the subproject's `RUN-update_upload_to_server.sh` to refresh symlinks |
| Two parallel branches for one unit on the landing page | A stale `workflow-RUN_N-*` has an `upload_manifest.tsv` | See the "canonical-RUN problem" in [Publishing workflow](#publishing-workflow) |

---

## Configuration parsing

The server uses a **built-in YAML parser** in `ai/gigantic_server.py` —
no PyYAML dependency. It supports:

- Scalar values (`key: value`)
- Lists (`- item`)
- One-level maps (`key:\n  subkey: value`)

It does **not** support: nested maps beyond one level, multi-line strings,
YAML anchors / aliases.

`RUN-start_server.sh` reads `execution_mode` and the `slurm.*` values from
the YAML using its own small Python helper (also limited to the same
subset).

---

## Publishing workflow

The rest of this guide is the **publishing process** — how a subproject's
pipeline outputs reach the server. This was the content of the former
`AI_GUIDE-publishing.md`; it lives here because the natural home for
publishing-to-server documentation is the server's own AI guide.

### Architecture

```
per-workflow upload_manifest.tsv      ┐
  (one per workflow-RUN_*/ dir)       │
                                      ├── <subproject>/RUN-update_upload_to_server.sh
gigantic_project-COPYME/server/ai/    │   (thin wrapper around the shared helper)
  update_upload_to_server.py          ┘
                                      │
                                      v
<subproject>/upload_to_server/<unit>/STEP_*/workflow-RUN_*/N-output/
  <symlinks to actual output files>
  .section_metadata.tsv   (auto-generated sidecar for the UI)
                                      │
                                      v
gigantic_server.py reads upload_to_server/ directly
  (auto-refreshes every refresh_interval_seconds — default 300s — no restart)
```

The server is a long-running process (long SLURM job or local foreground).
For data updates the user does not touch it — publish, wait up to
~5 minutes, refresh the browser.

### Discovery rules (important)

`update_upload_to_server.py` does `rglob('upload_manifest.tsv')` over each
subproject and **only processes manifests whose direct parent directory
name starts with `workflow-RUN_`**:

- `workflow-COPYME-*/upload_manifest.tsv` — **ignored** (template only)
- `workflow-RUN_1-*/upload_manifest.tsv` — **picked up**
- `workflow-RUN_2-*/upload_manifest.tsv` — **also picked up**

That last point is the canonical-RUN gotcha — see below.

### Manifest format

Tab-separated, header row required, lives at
`<workflow-RUN_*>/upload_manifest.tsv`:

| Column | Meaning |
|---|---|
| `source_path` | Glob, relative to the workflow dir (e.g., `OUTPUT_pipeline/3-output/*.mafft`) |
| `include` | `yes` or `no` (only `yes` publishes; `no` is silently skipped) |
| `dest_name` | Optional override of filename in `upload_to_server/` (blank = source basename) |
| `display_label` | UI title (blank = filename) |
| `file_category` | Grouping label — suggested set: `tree`, `alignment`, `visualization`, `qc`, `summary`, `sequences` |
| `description` | UI tooltip / subtitle |
| `order` | Integer sort key within category (lower = earlier; default 100) |

Lines starting with `#` are comments. Each subproject's per-step COPYME
template lives at `<subproject>/<unit>_COPYME/STEP_N-*/workflow-COPYME-*/upload_manifest.tsv`.

### The canonical-RUN problem (CRITICAL — research integrity)

When a workflow fails and gets retried, you can end up with
`workflow-RUN_1`, `workflow-RUN_2`, `workflow-RUN_3` in the same step
directory. The "real" outputs live in the latest successful one, and
`<subproject>/output_to_input/<unit>/STEP_*/` symlinks point to it.
That target RUN is **canonical**. The others are stale.

If you place a manifest in a stale RUN dir, the helper publishes whatever
partial outputs are in it, **side-by-side** with the canonical RUN, with
no UI hint that one is stale. Collaborators see two trees / two
alignments for the same unit with no idea which is current. **This is a
research-integrity failure under `AI_BEHAVIOR.md`'s zero-tolerance rule
for silent artifacts.**

**Rule: only place a manifest in the canonical RUN per unit.**

How to find canonical (example for `trees_gene_families`, key file =
`*.fasttree`; adapt the file pattern to other subprojects):

```bash
SUB=<subproject>
for d in $SUB/output_to_input/*/; do
  fam=$(basename "$d")
  ftraw=$(ls $d/STEP_2-phylogenetic_analysis/*.fasttree 2>/dev/null | head -1)
  if [ -L "$ftraw" ]; then
    canonical=$(readlink "$ftraw" | grep -oE 'workflow-RUN_[0-9]+')
    echo "$fam -> $canonical"
  fi
done
```

Most are `workflow-RUN_1`. The exceptions need explicit handling. Verify
no manifests sit in non-canonical RUN dirs:

```bash
find $SUB -path '*/workflow-RUN_*/upload_manifest.tsv' \
  | while read m; do
      run=$(echo "$m" | grep -oE 'workflow-RUN_[0-9]+')
      fam=$(echo "$m" | sed 's|.*/<unit>-||;s|/STEP_.*||')
      # cross-check against canonical map; report any mismatch
    done
```

### Procedure

#### 1. Pre-flight survey (do not skip)

Answer these before touching anything:

- How many units (gene families, species sets, etc.) have completed
  outputs? (`ls <subproject>/output_to_input/`)
- How many `workflow-RUN_*` dirs exist per step? Extras = stale candidates.
- Which RUN is canonical per unit? (use the symlink-readlink trick above)
- Are there units with partial outputs that should NOT publish? (compare
  what's in `OUTPUT_pipeline/` vs what the manifest globs would catch)

#### 2. Decide manifest defaults with the user

Common COPYME defaults for `trees_gene_families` (other subprojects
similar):

| File category | Default | Notes |
|---|---|---|
| Tree newicks (FastTree, IQ-TREE, VeryFastTree, PhyloBayes) | `yes` | Primary scientific artifact |
| MAFFT alignment | `no` | Flip on for transparency |
| ClipKit-trimmed alignment | `no` | The actual tree input — useful for reproducibility |
| IQ-TREE companion (`.contree`, `.iqtree` report) | `no` | Optional QC |
| STEP_1 final FASTA (e.g. AGS) | `yes` (template) | Many old STEP_1 RUN dirs lack manifests entirely |
| STEP_3 visualizations (PDF, SVG, summary) | `yes` | Default for collaborator browsing |

**Do NOT silently flip defaults.** Surface every category to the user
and ask. Document the resulting choices in your conversation.

#### 3. Edit the COPYME manifest(s)

Use `Edit` on `<workflow-COPYME-*>/upload_manifest.tsv`. Single source of
truth — never hand-edit individual RUN copies.

#### 4. Propagate to canonical RUNs only

```bash
SUB=<subproject>
COPYME=$SUB/<unit>_COPYME/STEP_N-<name>/workflow-COPYME-<name>/upload_manifest.tsv

for d in $SUB/output_to_input/*/; do
  unit=$(basename "$d")
  # determine canonical_run for this unit (see "canonical-RUN problem" above)
  canonical_run="workflow-RUN_1-<name>"   # adjust per unit using the symlink-readlink trick
  dest=$SUB/<unit>-${unit}/STEP_N-<name>/${canonical_run}
  cp "$COPYME" "$dest/upload_manifest.tsv"
done
```

For units with no completed output ("stalled"): drop the manifest into
RUN_1 — it will publish nothing now and pick up automatically when the
workflow finishes.

#### 5. Verify no stale manifests remain

```bash
find $SUB -path '*/workflow-RUN_*/upload_manifest.tsv'
# cross-check each path's RUN_N against the canonical map; remove any
# in non-canonical RUNs
```

#### 6. Dry-run

```bash
bash $SUB/RUN-update_upload_to_server.sh --dry-run > /tmp/dryrun.log 2>&1
tail -10 /tmp/dryrun.log   # check Files linked / Warnings
```

Expect a high warnings count — these are empty-glob notices for tree
methods you did not run (VeryFastTree, PhyloBayes, partial IQ-TREE
coverage, fasttree on stalled units). They are NOT errors. Cross-check
by computing expected misses (yes-entries in manifest × units that lack
the matching files); the count should match exactly.

`--dry-run` does NOT exercise the stale-prune step unless you also
pass `--clean`.

#### 7. Live run

```bash
bash $SUB/RUN-update_upload_to_server.sh
```

Automatic: stale-symlink prune, broken-symlink removal, empty-dir
cleanup, sidecar `.section_metadata.tsv` regeneration. Output reports:

```
Files linked: <N>
Warnings:     <M>
Stale symlinks removed:  <K>
Broken symlinks removed: <J>
Empty dirs pruned:       <L>
```

#### 8. Verify on disk

```bash
find -L $SUB/upload_to_server -type f -name '*.fasttree' | wc -l
find -L $SUB/upload_to_server -type f -name '*.mafft'    | wc -l
# spot-check a unit you know used a non-RUN_1 canonical
```

#### 9. Wait

Up to `refresh_interval_seconds` (default 300) for the live server to
refresh its file listing. No restart needed.

---

## Adding a new subproject to the server

1. Create `upload_manifest.tsv` in the subproject's `upload_to_server/`
   directory (or in each per-unit `workflow-RUN_*/` directory if the
   subproject has units).
2. Run the subproject's `RUN-update_upload_to_server.sh` to populate
   `upload_to_server/` with symlinks.
3. Add the subproject's name to `subproject_order:` in
   `START_HERE-server_config.yaml`.
4. Restart the server (the `subproject_order` change requires it).

---

## Server-side knobs (rarely needed)

`START_HERE-server_config.yaml`:

- `execution_mode:` — `local` or `slurm`
- `port:` — server port (default 9456)
- `subproject_order:` — explicit allowlist of which subprojects appear
  on landing page (and their order)
- `show_empty_subprojects: true|false` — show "NO DATA YET" placeholders
  for listed-but-empty subprojects
- `refresh_interval_seconds:` — file-listing refresh interval
- `exclude_file_patterns:` — substrings of filenames to hide (sidecar /
  state files already excluded)
- `slurm.*` — used only when `execution_mode: "slurm"`

Restart the server only when changing `port`, `subproject_order`,
`execution_mode`, or other config values that affect startup — **never
just for new published data** (auto-refreshes within
`refresh_interval_seconds`).

---

## Questions to ask the user

| Situation | Ask |
|---|---|
| Setting up server for first time | "Which subprojects should be served? I'll put them in `subproject_order`." |
| Adding a new subproject | "Does `upload_manifest.tsv` exist in its canonical RUN dir?" |
| Port conflict | "What port would you like to use?" |
| SLURM setup | "What are your SLURM account and QOS?" |
| Large data sync | "Some files are very large. Sync all or select specific BLOCKs?" |
| Publishing decisions | "For this file category, default is X — keep or flip?" (one row of the manifest defaults table per ask) |

---

## Common errors / red flags during publishing

| Symptom | Cause | Fix |
|---|---|---|
| Unit appears empty on the server | No manifest in the canonical RUN, or manifest globs match no files | `find $SUB/<unit>-<name>/STEP_*/workflow-RUN_*/upload_manifest.tsv`; check `OUTPUT_pipeline/` contents |
| Two parallel RUN branches for one unit | Manifest exists in a stale RUN | Delete stale manifest, re-run publisher |
| `Files linked: 0` in real run | All `include=no`, or all globs miss | Inspect manifest content; inspect `OUTPUT_pipeline/` |
| Many broken symlinks | Workflow output moved/deleted | Re-run publisher (auto-cleans broken); fix the sources upstream |
| Server shows old data | Cache TTL not yet elapsed | Wait `refresh_interval_seconds`; or restart server |
| Many warnings in dry-run | Tree methods listed `yes` but never ran (VeryFastTree, PhyloBayes, etc.) | Normal — informational, count should match expected misses |
