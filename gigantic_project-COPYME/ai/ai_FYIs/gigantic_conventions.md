# GIGANTIC Conventions

Canonical conventions for the GIGANTIC framework. Each entry is verified against the codebase.

This file grows as conventions surface during per-directory documentation review.
At the end of cleanup, this is the source for writing the top-level `GIGANTIC/` and
`gigantic_project-COPYME/` README + AI_GUIDE pairs.

**How to refer to conventions:** Each rule below is a **numbered section** (1–65).
In READMEs and other docs, refer to a rule by its **title** or as **convention N**
(e.g. "convention 2: `output_to_input/`"). Do not use the § symbol.

---

## 1. `research_notebook/` is a sandbox, outside GIGANTIC conventions — and there is ONE, at project root only

There is **exactly one** `research_notebook/` per project, at the
project root: `gigantic_project-COPYME/research_notebook/`. Per-subproject
`research_notebook/` directories are forbidden. (Earlier templates
allowed per-subproject and per-BLOCK/STEP sandboxes; that pattern was
consolidated — the per-subproject dirs were inconsistent in practice
and the chat-capture system always wrote to the project-root location
anyway.)

The project-root sandbox has:

- **No structure requirements** — any files, any naming, any subdirectory layout
- **No naming conventions** — users organize however they like

The only hard rule: **GIGANTIC must never pull from anything inside
`research_notebook/`.** Workflows, scripts, and pipelines treat it as
invisible.

If a user wants GIGANTIC to use a file that lives in
`research_notebook/`, they symlink it into
`gigantic_project-COPYME/INPUT_user/` (the canonical project-level
input directory). GIGANTIC reads from `INPUT_user/`, never from
`research_notebook/`.

This separation is what lets `research_notebook/` stay completely
free-form while GIGANTIC's reproducibility guarantees remain intact.

**Per-subproject scoping** (when useful): organize inside the project-root
sandbox with `subproject-<name>/` subdirs, e.g.:

```
research_notebook/
├── research_user/
│   ├── subproject-genomesDB/   # user's per-subproject scratch
│   ├── subproject-phylonames/
│   └── species70/              # or any user-defined organization
└── research_ai/
    ├── sessions/               # chat captures (per convention 9)
    └── subproject-phylonames/  # AI-side per-subproject scratch (when needed)
```

But this is a convenience pattern, not a requirement — the sandbox is free-form.

---

## 2. Inter-subproject data flow: `OUTPUT_pipeline/` → `output_to_input/` symlinks

Real data lives in `OUTPUT_pipeline/` inside each workflow-RUN directory. To share
specific outputs with downstream subprojects:

- A subproject exposes its sharable outputs at `<subproject>/output_to_input/`
  (lowercase `o`)
- Entries inside `output_to_input/` are **symlinks** pointing into the canonical
  `OUTPUT_pipeline/` of the appropriate `workflow-RUN_N-*` directory
- The directory structure inside `output_to_input/` is organized by
  `STEP_<N>-<name>/` or `BLOCK_<name>/` subdirectories matching the
  producer's structure. This keeps sequential runs from overwriting each
  other and preserves clear provenance (consumer sees which step generated
  what)

Downstream subprojects always read from `<upstream_subproject>/output_to_input/`,
never from inside an `OUTPUT_pipeline/` directly.

**GIGANTIC v1.0**: real files in `OUTPUT_pipeline/` use **stable filenames**
(convention 31). **GIGANTIC v2.0** will add optional run-date suffixes on archival
outputs while keeping **stable symlink names** in `output_to_input/` — see
convention 65.

**Note on a deprecated pattern**: an older CLAUDE.md described an `OUTPUT_to_input/`
(uppercase `O`) archival mirror inside each `workflow-RUN_N-*` directory. That
pattern is **not** implemented in any current GIGANTIC workflow code or
documentation — verified by full-tree grep (0 mentions in `.md`, `.nf`, `.py`,
`.sh`; 0 directories on disk inside the framework). Treat the lowercase symlink
pattern above as the only `output_to_input` convention.

---

## 3. AI guide files are always named `AI_GUIDE.md` — no suffixes

Just like README files are always `README.md`, AI guide files are always
`AI_GUIDE.md` — no descriptor suffix, no level suffix, no workflow-name suffix.

- `README.md` and `AI_GUIDE.md` are the only two doc filenames at every level
- The directory the file lives in establishes its scope (project, subproject,
  BLOCK/STEP, workflow). No need to repeat that scope in the filename.
- Old patterns like `AI_GUIDE-project.md`, `AI_GUIDE-trees_species.md`,
  `AI_GUIDE-trees_species_workflow.md`, `AI_GUIDE-phylonames_workflow.md` are
  all deprecated. Each should be renamed to `AI_GUIDE.md` in its own directory.

This convention was established earlier in development but drifted across
sessions; it is being re-enforced as part of the documentation cleanup pass.

---

## 4. The GIGANTIC repo is everything from `GIGANTIC/` downward

The GitHub-versioned project is the `GIGANTIC/` directory. Anything upstream of
it — parent directories, sibling user workspaces, lab-specific scaffolding — is
user research context and has **no relevance to GIGANTIC** or its conventions.

For example, in the development environment used to build GIGANTIC, the repo
lives inside `…/ai_ctenophores/github-gigantic_1/GIGANTIC/`. The
`ai_ctenophores/` directory is the developer's personal research workspace; it
is not part of GIGANTIC, does not constrain GIGANTIC, and does not appear in
any path users will see.

---

## 5. Paths inside `gigantic_project-COPYME/` are written relative to it

Once a path falls inside `gigantic_project-COPYME/` (or its renamed copy in a
user's project, e.g. `gigantic_project-cephalopod_evolution/`), document it
relative to that directory — not absolute, and not relative to the GIGANTIC
repo root.

- ✅ `subprojects/phylonames/STEP_1-generate_and_evaluate/`
- ✅ `ai/ai_FYIs/gigantic_conventions.md`
- ❌ `gigantic_project-COPYME/subprojects/phylonames/STEP_1-generate_and_evaluate/`
- ❌ `/blue/moroz/share/edsinger/.../gigantic_project-COPYME/subprojects/phylonames/STEP_1-generate_and_evaluate/`

This makes documentation portable across renamed project copies and across
machines. The user reads their `gigantic_project-<name>/` as the root of their
work; docs should respect that frame of reference.

---

## 6. AI-related infrastructure lives under `ai/`

All AI-related infrastructure inside `gigantic_project-COPYME/` is consolidated
under one top-level directory: `ai/`. This makes the AI plumbing visually
obvious to users browsing the project tree.

Current layout:

```
gigantic_project-COPYME/
├── ai/
│   ├── README.md                # What's in ai/
│   ├── ai_FYIs/                 # Markdown notes, conventions, archives, FYIs
│   │   └── gigantic_conventions.md
│   └── ai_scripts/              # Python tooling (capture hook, "Save Chat!" script, etc.)
│       ├── 002_ai-python-hook_precompact_capture_transcript.py
│       └── 003_ai-python-copy_session_jsonls.py
└── …
```

Anything new that is AI-internal goes under `ai/`. Anything user-facing
(`README.md`, `INPUT_user/`, `subprojects/`, etc.) stays at project root or in
its appropriate user-facing location.

---

## 7. `.claude/` exception: `gigantic_project-COPYME/.claude/` ships the capture hook + its docs

**General rule**: no `.claude/` directories anywhere in GitHub. Claude Code
session settings are developer-personal and gitignored everywhere by default.

**Deliberate exception**: `gigantic_project-COPYME/.claude/` ships **exactly
three files**, all tracked:

- `settings.json` — registers the PreCompact hook that calls
  `ai/ai_scripts/002_ai-python-hook_precompact_capture_transcript.py` to
  capture full lossless session transcripts to
  `research_notebook/research_ai/sessions/` before each context compaction.
- `README.md` — explains what this `.claude/` is and why it ships.
- `AI_GUIDE.md` — guard rails for AIs working inside `.claude/`.

Nothing else inside `gigantic_project-COPYME/.claude/` ships. The
`.gitignore` enforces this with: blanket `.claude/` ignore, then explicit
un-ignore of just these three files at this one path.

This exception exists because **Claude is the recommended AI for GIGANTIC** and
**lossless session capture is a primary GIGANTIC feature** (see convention 9). Without
the shipped hook config, each user would have to manually wire up capture in
their renamed project copy — defeating the "fresh AI session in renamed
project" model.

The exception is scoped tightly: only `gigantic_project-COPYME/.claude/`
ships, and only these three files inside it. `.claude/` at GIGANTIC root
and `.claude/` anywhere else stay fully gitignored.

---

## 8. AIs read `AI_*`, `CLAUDE.md`, and `README.md` on entry to any directory where they will work

At session start AND every time the working scope shifts to a new directory,
an AI should read the local guidance files if present:

- `CLAUDE.md` (Claude Code loads this automatically; other AIs should too)
- `AI_BEHAVIOR.md` (research-grade behavior; canonical, AI-agnostic)
- `AI_GUIDE.md` (how to work in this scope)
- `README.md` (project / subproject / workflow background)

"Working in a directory" means: about to edit, create, run, or otherwise
modify files in that directory or its descendants. Read-only exploration
(grep, ls, find) does not trigger this — but as soon as the AI is about to
do work, it should orient itself by reading these files.

Prevents the failure mode where an AI does 50 turns of work inside a deep
subdirectory without ever reading the local guidance, missing conventions or
constraints documented right there.

---

## 9. Chat-as-research-notebook: lossless permanent captures, never edited; "Save Chat!" for on-demand capture

Every AI chat session is treated as a research-notebook entry. The default
mechanism for Claude Code is fully automatic:

- The PreCompact hook (registered by `gigantic_project-COPYME/.claude/settings.json`)
  fires before every context compaction and gzip-copies the full JSONL
  transcript to `research_notebook/research_ai/sessions/`.
- Captures are **lossless** (full fidelity, every message, every tool call,
  every result), **permanent** (never auto-deleted by GIGANTIC), and
  **never edited** (treat as original lab-notebook entries).
- A `TRANSCRIPT_CAPTURE_LOG.md` in the sessions directory tracks each capture.

**On-demand capture via "Save Chat!"**: users can type **"Save Chat!"** to
their AI at any point to trigger an on-demand capture (the AI runs the
appropriate `ai/ai_scripts/` script). Recommended moments: at milestones,
before signoff, periodically during long sessions. AIs should also
proactively suggest capture when they sense the user is winding down
("done for the day", "let me stop here", closing-the-laptop signals) or
when a significant milestone has just completed.

**TTL gap** (worth knowing): Claude Code stores raw session JSONL at
`~/.claude/projects/<encoded-path>/*.jsonl` and auto-deletes after a default
30 days. The PreCompact hook captures only what's been through compaction.
To close the gap for short sessions that never compact:

1. Users should set `cleanupPeriodDays` to a large number in their global
   `~/.claude/settings.json` (one-line manual change), AND
2. The on-demand capture script (`ai/ai_scripts/003_ai-python-copy_session_jsonls.py`)
   raw-copies all `~/.claude/projects/...` JSONLs for this project into
   `research_notebook/research_ai/sessions/` so they survive TTL. AI runs
   it when the user types "Save Chat!" or proactively offers capture.

**Publication scrub**: captured transcripts may contain frank language, draft
hypotheses, collaborator names in unflattering context, credentials/tokens
that leaked into commands, etc. For public submission (journal supplementary
materials, etc.), make **copies** and scrub the copies. **Never modify the
originals** — they are the canonical research record.

**For non-Claude AIs** (Cursor, ChatGPT, Gemini, etc.): the principle is the
same — lossless, permanent, never-edited captures with on-demand "Save Chat!"
triggers. The mechanism differs by AI: see `AI_BEHAVIOR.md` and `AI_GUIDE.md`
in the project for AI-specific setup guidance. The non-Claude AI works with
the user to identify where their AI stores session data and to wire up an
equivalent periodic raw-copy into `research_notebook/research_ai/sessions/`.

---

## 10. Three documentation roles: CLAUDE.md, AI_GUIDE.md, README.md

Each level of the project carries up to three docs with **distinct audiences
and roles**:

| File | Audience | Role |
|------|----------|------|
| `CLAUDE.md` | AI | **Behavior / posture** in this work — research-grade, full documentation, transparency, archival, replication-enabling. *Not* technical conventions. |
| `AI_GUIDE.md` | AI | **How to work** in this directory / subproject / workflow — operational, navigational, "do X then Y." |
| `README.md` | User | **Biology + technology background**, technical specifics and requirements the user needs to know. |

Keep them in their roles. Don't drift technical conventions into `CLAUDE.md`;
don't drift user-facing background into `AI_GUIDE.md`. Each doc earns its
keep by serving exactly one audience.

---

## 11. `CLAUDE.md` is a one-line `@AI_BEHAVIOR.md` import

`AI_BEHAVIOR.md` holds the canonical research-grade behavior content (any
AI can read it directly). `CLAUDE.md` is one line — `@AI_BEHAVIOR.md` —
which Claude Code auto-loads-and-expands via its documented `@`-import
syntax. Single source of truth, no drift, no symlink fragility.

Verified Anthropic feature: `@path/to/file.md` import in CLAUDE.md is
supported (relative resolves from the file containing the import; max
5 hops of recursive imports).

---

## 12. AI attribution headers on AI-authored files

Every AI-authored script or substantive doc carries an attribution comment
block at the top. Two equivalent forms:

**Single-line (Python/bash scripts)**:
```python
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 25 | Purpose: Brief description
# Human: Eric Edsinger
```

**Multi-line HTML comment block (markdown docs)**:
```markdown
<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: One-paragraph statement of why this file exists
Scope:   What this file covers and what it does not
History:
  2026-05-25  Initial version (Opus 4.7).
============================================================================ -->
```

Markdown HTML comments are stripped by Claude Code before injection into
context, so they cost no AI context tokens.

---

## 13. Empty placeholder docs are an antipattern

Don't ship `README.md` or `AI_GUIDE.md` files that are 0 bytes or
"to-be-filled" stubs. Either fill them with real content, or delete them
and rely on the parent-directory docs.

An empty doc that other docs reference creates the worst combination:
the reader expects content (because it's referenced), opens the file, and
finds nothing. The empty-then-referenced `AI_GUIDE-project.md` in
`gigantic_project-COPYME/` and the empty `CLAUDE.md` in `GIGANTIC/` were
both surfaced and removed during the 2026-05-25 cleanup pass.

---

## 14. User flow: clone → copy template → rename → root AI session there

The canonical way to start a GIGANTIC project:

1. `git clone` the GIGANTIC repo
2. `cp -r GIGANTIC/gigantic_project-COPYME /path/outside/GIGANTIC/gigantic_project-<your-project-name>`
3. Start a **fresh, naive AI assistant session rooted at the renamed
   project directory** (not at `GIGANTIC/`)
4. All subsequent project work happens through AI sessions rooted at the
   renamed project.

Project naming convention: `gigantic_project-<your_project_name>`. The
copied directory lives **outside** the `GIGANTIC/` clone so framework
updates can be pulled without touching the user's project.

---

## 15. The renamed project directory is self-contained and archivable

Every input, output, workflow, subproject, AI session record, conda env
spec, and piece of project-specific documentation lives **inside** the
renamed `gigantic_project-<name>/` directory. The directory travels
independently of `GIGANTIC/` and can be archived (or shared with
collaborators) as the **complete record of one research project**.

Implication: no project-specific information should ever be required from
the surrounding GIGANTIC clone or from the user's broader machine —
everything needed must live inside the renamed project (or under
`~/.claude/`, which is per-user not per-project).

---

## 16. Framework-development sessions are a separate scope

AI sessions rooted at `GIGANTIC/` are for **framework development** —
improving the template, conventions, top-level docs. They are not for
project work.

This is why the research-grade behavior docs (`CLAUDE.md`,
`AI_BEHAVIOR.md`) live at the `gigantic_project-COPYME/` level, not at
`GIGANTIC/` root: research-grade posture is project-scope.

If a user opens an AI session at `GIGANTIC/` and asks for project work,
the AI redirects them per the project root's `AI_GUIDE.md`.

---

## 17. INPUT_user is the single staging arena between user data and GIGANTIC

There is **one and only one** `INPUT_user/` directory in any GIGANTIC
project: at `gigantic_project-COPYME/INPUT_user/`. It is the **sole**
interface through which the user makes outside data available to GIGANTIC
subprojects. No other path through which user data reaches subprojects
exists by design.

Inside subprojects, individual workflows may download outside resources
specific to their needs (e.g., reference databases); that handling is
per-subproject. But anything the user themselves provides flows through
`INPUT_user/`.

---

## 18. INPUT_user contains symlinks (relative, via `ln -srf`), not data files — at any depth

All non-doc content inside `INPUT_user/` — at every depth, including
subproject-specific subdirs like `INPUT_user/phylonames/user_phylonames.tsv`
or `INPUT_user/genomic_resources/genomes/<species>.fasta` — is a **symlink**
into `research_notebook/research_user/` (the user's sandbox per convention 1).

Use **relative** symlinks: `ln -srf <target> <link>` creates them
automatically. Relative symlinks survive when the entire project is moved,
copied to another machine, or archived. Absolute symlinks break.

The user's actual files live in `research_notebook/research_user/`
unstructured per convention 1; `INPUT_user/` exposes specific files to GIGANTIC via
deliberate symlinks. The symlink graph of `INPUT_user/` is the complete
catalog of what the project feeds into GIGANTIC.

Audit commands:
- `find INPUT_user -xtype l` — broken symlinks (sandbox file moved or deleted)
- `find INPUT_user -type l -exec ls -la {} \;` — all symlinks and their targets

---

## 19. INPUT_user structure is subproject-driven

The conventional subdirectories inside `INPUT_user/` (e.g., `species_set/`,
`genomic_resources/{genomes,proteomes,annotations,maps}/`, `phylonames/`)
reflect what current GIGANTIC subprojects expect. The structure is not
hard-coded by the framework — it grows as subprojects declare their input
requirements.

When a new subproject needs a new kind of user-provided input that
doesn't fit existing locations, the convention is:

1. Add the new subdir under `INPUT_user/<subproject>/` (or extend an
   existing subdir if the input type fits).
2. Add a `README.md` in the new subdir describing what gets staged there.
3. Document the requirement in the subproject's own docs as well.
4. Update `INPUT_user/README.md` if the new convention is broad.

This is mirrored by convention 22 below: `ai/ai_FYIs/` uses similar subproject-first
naming for related documents.

---

## 20. INPUT_user ships only documentation; user content is gitignored

The shipped GIGANTIC template provides only the doc scaffold inside
`INPUT_user/` (README.md, AI_GUIDE.md, subdir READMEs). All actual user
content — symlinks, manifests, species lists, custom phyloname overrides
— is gitignored. The user's project-specific staging arena stays on their
local disk only.

`.gitignore` enforces this with: `**/gigantic_project-COPYME/INPUT_user/**`
ignored, with `*.md` files un-ignored at any depth so the doc scaffold
travels with the template.

---

## 21. AI scripts: `NNN_ai-<lang>-<descriptor>.<ext>` naming

Scripts inside `ai/ai_scripts/` (and any AI-authored scripts elsewhere)
follow the convention:

```
NNN_ai-<lang>-<descriptor>.<ext>
```

- `NNN` — sequential three-digit number (001, 002, 003, ...)
- `_ai-` — marks the script as AI-authored
- `<lang>` — language indicator (`python`, `bash`, etc.)
- `<descriptor>` — concise underscore-separated description
- `<ext>` — file extension matching the language

Examples:
- `002_ai-python-hook_precompact_capture_transcript.py`
- `003_ai-python-copy_session_jsonls.py`
- `004_ai-bash-create_output_to_input_symlinks.sh`

When a script is invoked by another system (a hook, another script), the
invoking system uses the **literal filename** — not wildcards like
`003_*.py` — so future siblings (e.g., `003_X-other.py`) don't create
ambiguity.

---

## 22. `ai/ai_FYIs/` file naming: subproject-prefix where applicable

Files inside `ai/ai_FYIs/` follow this naming hierarchy:

- **Subproject-specific docs**: prefix with the subproject name —
  `<subproject>-<descriptor>.md` (e.g., `phylonames-overview-old.md`,
  `trees_gene_groups-HANDOFF-2026may25-snap_family_and_step2_3_state.md`).
  This keeps related FYIs sorted together alphabetically.
- **Project-wide docs**: no subproject prefix
  (e.g., `gigantic_conventions.md`, `NEXTFLOW_26_COMPATIBILITY.md`,
  `publication_scrub_guide.md`).
- **Archived versions of deprecated docs**: suffix with `-old`
  (e.g., `phylonames-overview-old.md`).

---

## 23. NextFlow source files use `${projectDir}` for path construction

The relative-path convention (convention 5) holds for NextFlow `.nf` files via the
`${projectDir}` idiom. `${projectDir}` is a NextFlow built-in that
resolves to the absolute path of the directory containing the running
`main.nf` at runtime.

```groovy
script:
"""
python3 ${projectDir}/scripts/001_ai-python-validate_inputs.py \\
    --config ${projectDir}/../START_HERE-user_config.yaml \\
    --output_dir ${projectDir}/../${params.output.base_dir}
"""

publishDir "${projectDir}/../${params.output.base_dir}/1-output", mode: 'copy'
```

Source stays portable (paths are relative to `projectDir`); resolved
paths at runtime are absolute (and unique per workflow run). Both
properties hold simultaneously — no exception to convention 5 is needed for
NextFlow.

---

## 24. NextFlow runtime artifacts are gitignored

Files NextFlow generates at run time contain absolute paths and per-run
state. They never ship with the template:

- `work/` — staging directory for process executions
- `.nextflow/` — internal NextFlow state
- `.nextflow.log*` — NextFlow logs
- `.params.json` — per-run flattened-JSON params file (contains absolute
  paths from `${projectDir}` expansion)

All four are in `.gitignore`. When clearing a stuck run, deleting these
+ re-running fresh (no `-resume`) is the canonical reset.

---

## 25. `research_user/` ships as empty directory; `research_ai/` ships with documentation

Refines convention 1 (and applies only to the single project-root
`research_notebook/` — per-subproject `research_notebook/` directories
are forbidden):

- `research_notebook/research_user/` is the user's wild-west sandbox. The
  template ships only the empty directory (`.gitkeep` only — no README,
  no scaffolding). Per convention 1, GIGANTIC never reaches into it; users
  organize however they want.
- `research_notebook/research_ai/` is **GIGANTIC's own sandbox**.
  Documentation appropriate to AI infrastructure (capture system, etc.)
  ships here, including `README.md` and the `sessions/.gitkeep` so the
  capture destination is preserved.

Captured session transcripts (per convention 9) land in
`research_notebook/research_ai/sessions/` and are gitignored as runtime
content — they never ship.

---

## 26. TRANSCRIPT_CAPTURE_LOG.md schema and trigger vocabulary

The capture log written by 002 (hook) and 003 (Save Chat! script) uses
exactly this schema:

```markdown
| Date | Session ID | Model | Trigger | Transcript Size | Output File |
|------|------------|-------|---------|-----------------|-------------|
```

**Trigger values**:
- `auto` — PreCompact hook fired automatically
- `manual` — PreCompact hook invoked manually
- `save_chat` — On-demand "Save Chat!" via 003

Both scripts produce schema-compatible rows; they share the file.

---

## 27. Session capture filename format (Claude Code)

The PreCompact hook (002) and Save Chat! script (003) both produce
`.jsonl.gz` files in `research_notebook/research_ai/sessions/` with this
filename format:

```
YYYYMMDD_HHMMSS-claude_code-<model-with-underscores>-<8-char-session-id>.jsonl.gz
```

Example:
```
20260306_014426-claude_code-claude_opus_4_6-44529712.jsonl.gz
```

- Timestamp = last-message timestamp from the JSONL content (so the same
  source file at the same state produces the same destination filename,
  enabling idempotent re-runs)
- Model with hyphens replaced by underscores (e.g., `claude-opus-4-7` →
  `claude_opus_4_7`)
- First 8 characters of the session UUID

For other AIs, use an analogous format with the AI's name in the
`claude_code` slot.

---

## 28. Per-subproject conda environments — no central `conda_environments/`

Each subproject manages its own conda environment(s), usually defined in
the subproject's `ai/conda_environment.yml` (or per-tool yml files for
multi-tool subprojects). The subproject's `RUN-workflow.sh` creates the
environment lazily on first run if it doesn't already exist.

A central `gigantic_project-COPYME/conda_environments/` directory existed
in older GIGANTIC versions but is deprecated and removed. It produced a
disconnect between "where I'm working" and "where my env definition
lives"; the per-subproject pattern keeps everything co-located.

Env naming convention: `aiG-<subproject>-<block_or_step>-<optional_details>`
(established earlier; verify against subproject's `ai/conda_environment.yml`
header comment).

---

## 29. Unified `RUN-workflow.sh` is the canonical driver

Each workflow has a single canonical entry point: `RUN-workflow.sh`. It
handles local execution AND self-submits to SLURM when the YAML config's
`execution_mode` key is set to `slurm`. There is no separate
`RUN-workflow.sbatch` in the canonical pattern — that was an older
two-file approach now deprecated.

The unified driver:
- Reads `START_HERE-user_config.yaml`
- Sets up conda env on first run
- For SLURM: writes a per-run sbatch wrapper and submits it
- For local: invokes NextFlow directly
- Cleans up runtime artifacts on exit

The canonical example (most recently modernized) is the
`ocl_phylogenetic_structures/BLOCK_annotations_X_ocl/` workflow.

---

## 30. This file is the canonical source of truth for conventions

`gigantic_project-COPYME/ai/ai_FYIs/gigantic_conventions.md` is the
authoritative list of GIGANTIC conventions. Other documents reference
section numbers here rather than duplicating content:

```markdown
See `ai/ai_FYIs/gigantic_conventions.md` convention 9 for the chat-as-research-notebook
architecture.
```

When a convention is updated here, downstream references stay valid as
long as they point at section numbers. **Don't renumber existing
sections** — append new ones; if a section is genuinely deprecated, mark
it `~~convention N~~ DEPRECATED — see convention M`.

---

## 31. Pipeline output file naming: `N_ai-<descriptor>.<ext>`

Outputs written by pipeline scripts follow the convention:

```
N_ai-<descriptor>.<ext>
```

where `N` is the **invoking script's number with leading zeros removed**
(e.g., script `005_ai-python-generate_blast_commands.py` writes outputs
named `5_ai-blast_commands.sh` into `OUTPUT_pipeline/5-output/`).

Why drop leading zeros in outputs (vs script names which keep them)?
Output file lists are typically short enough that alphabetical sorting
doesn't need the leading zeros, and `5_ai-...` reads more naturally than
`005_ai-...`. Scripts retain `NNN` because directories accumulating many
scripts benefit from the zero-padding for ordering.

The pairing — `NNN_ai-script.py` → `OUTPUT_pipeline/N-output/N_ai-result.tsv` —
makes the script-to-output mapping immediately readable.

---

## 32. Python variable naming conventions

GIGANTIC Python code uses these naming patterns consistently:

| Pattern | Use for | Example |
|---------|---------|---------|
| `input_X` / `input_X_Y_Z` | All inputs (files, paths, data) | `input_fasta_all_species`, `input_genome_data` |
| `output_X` / `output_X_Y_Z` | All outputs (files, paths, data) | `output_arm_counts`, `output_summary_table` |
| `Xs___Ys` (three underscores) | Dictionaries; plural keys-set + plural values-set | `identifiers___sequences`, `species_names___genome_sizes` |
| `Xs` (plural) | Lists | `sequences`, `identifiers`, `genome_sizes` |
| `X` (singular) | Iteration variable inside a loop over `Xs` | `for sequence in sequences:` |
| `parts_X` | Result of splitting variable `X` | `parts_annotation_string = annotation_string.split('|')` |
| `line` + `parts` | TSV/CSV row parsing | `line = line.strip(); parts = line.split('\t')` |

Use full words, not abbreviations (`sequence_count` not `seq_cnt`).
Established scientific abbreviations (GO, Pfam, BLAST) are kept as-is.

---

## 33. Python spacing: spaces inside brackets (intentional PEP 8 deviation)

GIGANTIC Python uses spaces **inside** parentheses, square brackets, and
curly braces, and around operators. This intentionally deviates from PEP 8
in favor of human readability for the research audience.

```python
# GIGANTIC style
species_list = [ 'Octopus', 'Aplysia', 'Homo' ]
genome_data = { 'species': 'Octopus', 'size': 2700000000 }
if species_count == 8:
    open( 'species.fasta', 'r' )

# NOT GIGANTIC style (standard PEP 8)
species_list = ['Octopus', 'Aplysia', 'Homo']
genome_data = {'species': 'Octopus', 'size': 2700000000}
if species_count==8:
    open('species.fasta', 'r')
```

Readability for the human researcher takes precedence over PEP 8
conformance. Don't run black, ruff-format, or other auto-formatters
that would strip these spaces.

---

## 34. TSV/CSV output conventions: self-documenting headers + tab/comma delimiters

All tabular outputs follow two rules:

### Self-documenting column headers

```
header_ID (header details in human-readable prose)
```

- `header_ID`: underscore-separated identifier
- `header details`: prose explanation in parentheses, with spaces, embedding
  calculation method and data format where relevant

Examples:
```
Orthogroup_ID (orthogroup identifier from OCL data)
Conservation_Rate_Percent (calculated as conservation events divided by conservation plus loss events times 100)
Species_List (comma delimited list of species names in Genus_species format)
```

Headers can be long if needed — clarity is the priority.

### Delimiter convention

- **Between columns**: TAB (`\t`) — the file is a TSV
- **Within a column** (multi-value cells): COMMA (`,`) — pipes (`|`) are
  not used as in-column delimiters

```
# CORRECT (TSV with comma-delimited in-column lists)
Species_List (comma delimited list of species names)
Homo_sapiens,Mus_musculus,Drosophila_melanogaster

# INCORRECT (do not use pipes in columns)
Homo_sapiens|Mus_musculus|Drosophila_melanogaster
```

---

## 35. NextFlow workflow directory naming: template vs run instance

Each NextFlow workflow lives in a directory whose name encodes whether it
is a **template** (committed to git, the canonical source) or a **run
instance** (a user's working copy of that template).

| Form | Meaning | In git? |
|------|---------|---------|
| `workflow-COPYME-<descriptor>/` | Canonical template; the user copies it to run | Yes (tracked) |
| `workflow-RUN_NN-<descriptor>/` | A run instance — copy of the template that executed (or is executing) once. `NN` numbers sequential runs of that workflow. | No (gitignored — `workflow-RUN_*/`) |

Older naming patterns like `nf_workflow-TEMPLATE_NN-<descriptor>/` or
`workflow-RUN_NN_NN-<descriptor>/` are deprecated in favor of the simpler
`workflow-COPYME-*` / `workflow-RUN_NN-*` pair.

The run-instance dirs contain a workflow's full execution artifacts
(`OUTPUT_pipeline/`, `work/`, `.nextflow*`, slurm logs) and never ship
to git.

---

## 36. NextFlow fail-fast: no `optional: true` outputs; `errorStrategy = 'terminate'`; `sys.exit(1)` on missing data

Research pipelines must fail loudly on missing or invalid data — not
silently continue with placeholder values or empty files. Three rules
enforce this:

### Never use `optional: true` in NextFlow outputs

```groovy
// ❌ WRONG — allows silent missing-output to succeed
output:
    path "results.txt", emit: results, optional: true

// ✅ CORRECT — pipeline errors if file is missing
output:
    path "results.txt", emit: results
```

If a process can legitimately produce no output, fix the process to
produce an empty-with-headers file rather than no file. Marking outputs
optional means downstream consumers see "no error" while having no data.

### `errorStrategy = 'terminate'` and `maxErrors = 0` in `nextflow.config`

```groovy
process {
    errorStrategy = { task.attempt <= 2 ? 'retry' : 'terminate' }
    maxRetries = 2
    maxErrors = 0   // stop immediately on first persistent failure
    // Never use errorStrategy = 'ignore'
}
```

Research pipelines want immediate feedback when something goes wrong, not
to discover multiple failures hours later.

### Python pipeline scripts: `sys.exit(1)` on missing data

```python
if not critical_data:
    logger.error( "CRITICAL ERROR: What went wrong" )
    logger.error( "Why this is a problem" )
    logger.error( f"Relevant context: { details }" )
    logger.error( "How to fix it" )
    sys.exit( 1 )   # FAIL
```

Never `sys.exit(0)` when data is missing. Never log "warning" for a
critical issue. Never write a placeholder/empty file and continue. The
script either produced the expected output or it failed — no third state.

---

## 37. Project-level data server: one per project, at `server/`

Each GIGANTIC project ships **one** centralized data server at
`gigantic_project-COPYME/server/`. It is a long-running web service that
gives collaborators HTTP access to selected pipeline outputs across all
subprojects of the project. There is no per-subproject server; subprojects
publish into the single project-level server.

The server is operated through a unified `RUN-start_server.sh` driver
(convention 29) governed by `execution_mode` in `START_HERE-server_config.yaml`.
Full documentation lives in `server/README.md` (user-facing) and
`server/AI_GUIDE.md` (operation + publishing workflow).

---

## 38. Subproject-to-server interface: `<subproject>/upload_to_server/` + manifests + symlinks

Each subproject exposes selected outputs to the project's data server
through a fixed interface:

- **`<subproject>/upload_to_server/`** is the single publish destination
  per subproject (subproject-level; **never per-STEP, per-BLOCK, or
  per-workflow-RUN** — consumers and the server look in exactly one
  place per subproject). The current state of any subproject with
  `<STEP>/upload_to_server/` dirs is a legacy deviation to be refactored.
- Internal structure inside `upload_to_server/` is **user-facing** —
  organized for collaborators to browse the project, not for GIGANTIC's
  internal bookkeeping. The shared helper's default is to mirror
  producer paths:
  ```
  <subproject>/upload_to_server/
    └── STEP_<N>-<name>/         (or BLOCK_<name>/, or unit-name/)
        └── workflow-RUN_<K>-<name>/   (canonical RUN per convention 39)
            └── N-output/
                └── <file>       (symlink to the actual output)
  ```
  This default works well when the natural collaborator-facing framework
  IS the producer's structure. Per-manifest `dest_name` overrides can
  reshape paths into a user-defined framework when the natural framework
  for collaborators differs from the internal pipeline layout (e.g.,
  grouping by species set, by hypothesis, by deliverable type rather
  than by STEP).

  Note distinction from `output_to_input/` (convention 2): `output_to_input/`
  structure **mirrors producer paths** mandatorily (preserves provenance
  for downstream subprojects); `upload_to_server/` structure is for
  human collaborators and **can deviate** from producer paths when a
  different organization serves the user better.
- Each canonical `workflow-RUN_*/` carries its own
  **`upload_manifest.tsv`** controlling which of its outputs publish
  (one manifest per canonical RUN dir; see convention 39)
- Each subproject has a **`RUN-update_upload_to_server.sh`** at
  subproject level that invokes the shared helper at
  `gigantic_project-COPYME/server/ai/update_upload_to_server.py`. The
  shared helper walks the subproject, finds every `upload_manifest.tsv`
  inside any `workflow-RUN_*/`, and assembles the nested
  `upload_to_server/` tree above.
- The server reads `upload_to_server/` symlinks transparently — **there
  is no copy or sync step**. Follow-the-symlink at HTTP request time.

This parallels the `output_to_input/` symlink pattern (convention 2) but serves a
different consumer (the data server / collaborators, not downstream
subprojects).

`upload_to_server/` ships only `.gitkeep` + `README.md` + `upload_manifest.tsv`
(canonical templates of the manifest); actual published symlinks are
gitignored as runtime content.

---

## 39. Canonical-RUN rule for publishing — ONE manifest per unit, in the canonical RUN only

When a subproject's workflow has been retried multiple times, the
filesystem can hold `workflow-RUN_1`, `workflow-RUN_2`, `workflow-RUN_3`
in the same step directory. The **canonical** RUN is the one whose
`OUTPUT_pipeline/` is symlinked from `<subproject>/output_to_input/`.
The others are stale.

**Rule**: place `upload_manifest.tsv` **only** in the canonical RUN per
unit. Never leave a stale RUN with its own manifest.

**Why**: if a stale RUN keeps a manifest, the publisher copies its
(partial / wrong / outdated) outputs into `upload_to_server/`
side-by-side with the canonical RUN's outputs. The server then shows
collaborators **two trees** or **two alignments** or **two structure
sets** for the same unit, with no UI hint that one is stale. This is a
**research-integrity failure** under `AI_BEHAVIOR.md`'s zero-tolerance
rule for silent artifacts.

How to find the canonical RUN per unit (example pattern; adapt the file
glob to the subproject):

```bash
SUB=<subproject>
for d in $SUB/output_to_input/*/; do
  unit=$(basename "$d")
  raw=$(ls $d/STEP_*/<canonical-file-glob> 2>/dev/null | head -1)
  if [ -L "$raw" ]; then
    canonical=$(readlink "$raw" | grep -oE 'workflow-RUN_[0-9]+')
    echo "$unit -> $canonical"
  fi
done
```

When in doubt during a publish: dry-run the publisher
(`RUN-update_upload_to_server.sh --dry-run`) and reconcile the file
counts before going live.

Full publishing workflow lives in `server/AI_GUIDE.md` ("Publishing
workflow" section).

---

## 40. Bidirectional discoverability: producer AI_GUIDEs list their consumers

When a subproject, STEP, BLOCK, or workflow **consumes** data from
another subproject's `output_to_input/`, update the **producer's**
relevant AI_GUIDE to note the consumer. This bidirectional cross-
reference makes the data-flow graph navigable from either end.

**Example**: trees_species' STEP that produces species-tree structures
gets a note in its AI_GUIDE saying "downstream consumers:
`ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/` reads these structures;
`ocl_phylogenetic_structures/BLOCK_annotations_X_ocl/` reads them via the
sibling BLOCK's `output_to_input/`."

**Why**: an AI walking into a subproject and finding it produces data
should be able to answer "who uses this?" without grep'ing the whole
tree. The producer-side reference solves this directly. Without it, you
need a separate dependency map (drifts) or a cross-tree search (slow,
incomplete).

**How**: add a "Downstream consumers" section to the producer's relevant
AI_GUIDE (the one closest to the output_to_input/ source) when a
consumer relationship is established. Keep it short:

```markdown
## Downstream consumers

The `output_to_input/<subdir>/` exposed here is read by:

- **<consumer subproject>** — `<consumer subproject>/...` consumes
  `<which file(s) and what for>`. See `<consumer subproject>/AI_GUIDE.md`
  for the consumer side.
```

Apply when surfacing a new producer-consumer pair during cleanup or
during new development.

---

## 41. Subproject internal organization: three natural types (STEP, BLOCK, UNIT)

GIGANTIC subprojects come in three structural shapes, chosen to fit the
scientific use case. Internal structure is **subproject-natural** — do
not force a single shape on all subprojects. (Compare with the
**interface layer** — `upload_to_server/`, `output_to_input/`,
`RUN-update_upload_to_server.sh` at subproject root — which IS
standardized per convention 2, convention 38, etc., regardless of internal type.)

| Type | When to use | Internal layout | Examples |
|------|-------------|-----------------|----------|
| **STEP** | Sequential pipeline; STEP_<N+1> depends on STEP_<N> | `<subproject>/STEP_<N>-<descriptor>/workflow-COPYME-<name>/` | `phylonames` (STEP_1-generate_and_evaluate → STEP_2-apply_user_phylonames); `genomesDB` (STEP_1-sources → ... → STEP_4-create_final_species_set) |
| **BLOCK** | Parallel/alternative tools, methods, or analyses producing comparable outputs | `<subproject>/BLOCK_<descriptor>/workflow-COPYME-<name>/` | `orthogroups` (BLOCK_orthohmm, BLOCK_orthofinder, BLOCK_broccoli — pick your tool); `annotations_hmms` (BLOCK_interproscan, BLOCK_deeploc, BLOCK_signalp — different annotations); `hotspots` (BLOCK_self_blast, BLOCK_identify_hotspots) |
| **UNIT** | Per-unit instances of a templated workflow chain (each unit goes through the same STEP_1 → STEP_2 → ... pipeline) | `<subproject>/<unit_prefix>_COPYME/STEP_<N>/workflow-COPYME-<name>/` (template) and `<subproject>/<unit_prefix>-<name>/STEP_<N>/workflow-COPYME-<name>/` (per-unit instances) | `trees_gene_families` (gene_family_COPYME template + gene_family-<name> instances); `trees_gene_groups` (similar) |

**Mixed or hybrid types**: a subproject occasionally needs more than one
type (e.g., a STEP-organized subproject where one STEP has BLOCK
alternatives inside it). That's fine — apply the type that fits at each
level. Don't invent custom types.

**Naming**:
- `STEP_<N>-<descriptor>` — zero-padded number with descriptive suffix
- `BLOCK_<descriptor>` — no number; BLOCKs are alternatives, not ordered
- `<unit_prefix>_COPYME` for the unit template (e.g., `gene_family_COPYME`)
- `<unit_prefix>-<unit_name>` for unit instances (e.g.,
  `gene_family-innexin_pannexin_channels`)
- `workflow-COPYME-<descriptor>` for the workflow template inside any
  STEP/BLOCK/unit (convention 35)

---

## 42. "Where this fits" header on every doc

Every `README.md` and `AI_GUIDE.md` opens with a short **"Where this fits"**
block immediately after the AI-attribution comment block (convention 12), pointing
the reader UP, DOWN, IN, and OUT:

- **UP**: parent README + parent AI_GUIDE (one level up, and project root)
- **DOWN**: child docs (children's READMEs / AI_GUIDEs / workflow runbooks)
- **IN**: where the data this unit consumes comes from (INPUT_user
  staging, upstream subproject `output_to_input/`, conventions docs)
- **OUT**: where this unit's outputs go (`output_to_input/`,
  `upload_to_server/`, downstream consumer subprojects)

The block is **brief** (a 5-line bulleted list, not a section).

**Pattern**:

```markdown
## Where this fits

`<subproject_or_block>` is the <Nth> subproject/BLOCK you run
(<one-line orientation>).

- Parent project landing page: [`../../README.md`](../../README.md)
- Parent project AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- This unit's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Prerequisite: [`../<upstream>/`](../<upstream>/) (provides X)
- Next step: [`../<downstream>/`](../<downstream>/) (consumes Y)
```

**Why**: any AI or human walking into a directory cold can navigate the
project structure from the first 10 lines of the doc, without grep'ing
or asking. Adopted from the phylonames + genomesDB + trees_species deep
eval passes (2026-05-26).

---

## 43. Up/down/in/out is the canonical doc evaluation framework

When auditing any `README.md` or `AI_GUIDE.md`, check the four-axis
integration explicitly:

1. **UP** — Does it link to parent docs (parent README, parent
   AI_GUIDE, and the project-root pair)?
2. **DOWN** — Does it link to child docs (children's READMEs,
   workflow runbooks, BLOCK guides)?
3. **IN** — Does it name explicitly where this unit's inputs come
   from (INPUT_user staging slot, upstream subproject's
   `output_to_input/<path>/<file>`, NCBI / external data sources)?
4. **OUT** — Does it name explicitly where this unit's outputs go
   (`output_to_input/<subdir>/`, `upload_to_server/`, listed
   downstream consumer subprojects per convention 40)?

A doc missing any axis is incomplete. Use the framework as a checklist
during deep eval passes (it surfaced multiple integration gaps across
phylonames, genomesDB, and trees_species during the 2026-05-26 pass —
including the entire `BLOCK_user_requests` BLOCK that had shipped without
being added to its subproject README).

---

## 44. Deep eval: cross-check docs against code (main.nf / nextflow.config / scripts / YAML)

Doc-only review is **not enough** for deep eval. Every doc claim about
scripts, output paths, env names, or workflow structure must be
cross-checked against the actual file on disk:

| Doc claim | Source of truth |
|---|---|
| Script names + count | `ls workflow-COPYME-*/ai/scripts/` |
| Process names + execution order | `workflow-COPYME-*/ai/main.nf` |
| Conda env name | `workflow-COPYME-*/ai/conda_environment.yml` (`name:` line) |
| YAML keys, defaults, structure | `workflow-COPYME-*/START_HERE-user_config.yaml` |
| Process resources, error strategy | `workflow-COPYME-*/ai/nextflow.config` |
| Actual output filenames | `find workflow-RUN_*/OUTPUT_pipeline/` |
| Symlink targets | `ls -la <subproject>/output_to_input/*/maps/` |

The genomesDB workflow-level deep eval pass (2026-05-26, commit
`332e2f5`) surfaced multiple recurring doc-vs-reality mismatches that
sed cleanup could not catch — wrong script-count tables, fictional
script names, output paths off by one directory level, a fictional
`6_ai-species_selection_manifest.tsv` referenced across 5 docs that
never existed. **Cross-checking against code catches what doc-only
review misses.**

---

## 45. `write_run_log` is the canonical final script in every NextFlow workflow

Every workflow's NextFlow `main.nf` ends with a `write_run_log` process
that invokes `NNN_ai-python-write_run_log.py` (highest script number in
the workflow's `ai/scripts/` directory). The script writes a
timestamped per-run audit log to the workflow's `ai/logs/` directory.

This is **easy to forget in doc tables** — the recurring failure mode
is documenting "the 6 analysis scripts" without mentioning script 007
write_run_log, then someone reads the doc and is confused when there are
N+1 scripts on disk. Always include `write_run_log` in script tables;
mark it explicitly as the audit-log final step.

The script's role:
- Records workflow name, subproject name, project name, status, timestamp
- Writes to `ai/logs/run_YYYYMMDD_HHMMSS-<subproject>_success.log`
- Is **per-run** — separate from project-wide chat captures (convention 9), which
  live in `research_notebook/research_ai/sessions/`

---

## 46. Anti-pattern: nested `slurm:` block in `START_HERE-user_config.yaml`

Pre-convention 29 templates carried a nested YAML block:

```yaml
slurm:
  enabled: false
  account: "your_account"
  qos: "your_qos"
  memory: "4gb"
  time: "1:00:00"
  cpus: 1
```

This is **dead code** — convention 29's unified `RUN-workflow.sh` driver reads
only the flat keys at the bottom of the YAML:

```yaml
execution_mode: "local"        # or "slurm"
slurm_account: "your_account"
slurm_qos: "your_qos"
cpus: 2
memory_gb: 8
time_hours: 2
```

When found in a YAML, the stale nested `slurm:` block should be
removed. (Surfaced and removed from genomesDB STEP_1 YAML during the
2026-05-26 cleanup; verified absent in genomesDB STEP_2/3/4 + phylonames
STEP_1/2.)

---

## 47. Frozen-artifact rule: `workflow-RUN_*/` docs are historical, not canonical

When a `workflow-RUN_<K>-*/` directory exists alongside its
`workflow-COPYME-*/` template, the RUN dir is a **frozen research
artifact** — a snapshot of the workflow as it was when that specific
run happened. Its embedded `README.md` and `ai/AI_GUIDE.md` are
historical documentation of that run.

**Rule**: canonical-pattern refactors and doc-cleanup passes touch
**only** `workflow-COPYME-*` docs. Leave `workflow-RUN_*` docs alone.

**Why**: editing the RUN docs would rewrite the historical record of
what the workflow looked like when it executed. Reproducibility and the
research-notebook nature of the project require those artifacts stay
frozen.

(See also: convention 39 canonical-RUN rule for publishing — only the canonical
RUN gets a live `upload_manifest.tsv`; stale RUNs are left untouched.)

---

## 48. Quick Reference navigation table at top of every AI_GUIDE

Every `AI_GUIDE.md` carries a navigation table near the top, after the
AI-attribution block and the "Where this fits" block (convention 42), listing
**every related doc the reader might want next**:

```markdown
## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../AI_GUIDE.md` (project root) |
| Conventions (convention 1–convention 58) | `../../ai/ai_FYIs/gigantic_conventions.md` |
| <subproject> concepts | This file |
| <BLOCK or STEP> overview | `<BLOCK_or_STEP>/AI_GUIDE.md` |
| Running the workflow | `<...>/workflow-COPYME-*/ai/AI_GUIDE.md` |
| Downstream subprojects | `../<consumer>/AI_GUIDE.md` |
```

The Quick Reference is **denser than "Where this fits"** (convention 42) — it's a
full pointer-list for AI navigation, while "Where this fits" is a
3-sentence orientation. They serve different purposes and **both
appear** in every AI_GUIDE.

Adopted from the phylonames + genomesDB + trees_species deep eval
passes (2026-05-26). The pattern was already in some AI_GUIDEs before
the pass but not uniformly applied.

---

## 49. `z_*` gitignore pattern — early-development dirs visible, contents ignored

Parallels the existing `x_*` pattern but with different intent:

| Prefix | Intent | Lifecycle |
|--------|--------|-----------|
| `x_*`  | Staged for eventual removal | Was canonical, now superseded |
| `z_*`  | Staged as early-development, not for general use yet | Future-canonical |

Both sort to the ends of alphabetical listings.

By default, files and dirs prefixed with `z_` are gitignored. To make a `z_`
**directory** visible on github (so its presence signals future framework
direction in higher-level docs), add a `README.md` inside it — `README.md`
is the only filename un-ignored within `z_*` dirs.

Pattern in root `.gitignore` (the `**/` prefixes are necessary because `z_`
dirs can live at any depth):

```gitignore
z_*
!**/z_*/
**/z_*/**
!**/z_*/README.md
```

Without `**/`, the content-ignore rule fires only at the repo root and
misses the actual targets (e.g.,
`gigantic_project-COPYME/subprojects/z_foo/`).

Adopted 2026-05-26 (commit `dbe8d89`) after renames of
`ocl_perspectives → z_ocl_perspectives`,
`ocl_using_simple_taxonomy → z_ocl_using_simple_taxonomy`,
`parsimony_tree_structures → z_parsimony_tree_structures`,
`synteny → z_synteny`.

---

## 50. Per-subproject `research_notebook/` migration procedure

Per convention 1, per-subproject `research_notebook/` directories are forbidden;
content belongs in the single project-root sandbox under
`research_notebook/research_user/subproject-<name>/`. When deep-eval
encounters a surviving per-subproject `research_notebook/`, migrate in this
order:

1. **`mkdir -p`** the destination
   `gigantic_project-COPYME/research_notebook/research_user/subproject-<name>/`
2. **`git rm --cached`** any tracked files in the old `research_notebook/`
   (papers, summaries, manifests) — keeps them on disk, removes from index.
   Tracked content there is anomalous per convention 25; untrack rather than carry
   forward.
3. **`mv`** the remaining (already-untracked) directories and files to the
   destination via plain `mv` — gitignored at both old and new path.
4. **`git rm`** the per-subproject `.gitkeep`.
5. **`rmdir`** the now-empty per-subproject `research_notebook/`.

Document the move in the commit message including which files were
untracked (they remain on disk; user may later choose to re-track elsewhere
if a paper summary is intentionally part of the scientific record).

Migration order matters: `git rm --cached` must precede `mv` so the
destination doesn't end up holding a tracked-but-would-be-ignored file (a
confusing state).

Established across phylonames + genomesDB + trees_species (commit
`6186551`), trees_gene_families (commit `61ef05a`), annotations_hmms +
gene_sizes (commits `f763ba0`, `ab6ad1b`).

---

## 51. Missing-doc-create-on-deep-eval policy

When a deep-eval pass encounters a subproject, BLOCK, or workflow with no
`README.md` and/or no `AI_GUIDE.md` at the expected level, **create** the
missing docs from scratch — do not skip with "no docs to update."

Derive content from:
- `main.nf` top-of-file comments (design overview, process list)
- Top-of-file comments and docstrings in `ai/scripts/*`
- `START_HERE-user_config.yaml` (parameter shape, references)
- Directory structure (BLOCKs, STEPs, workflow templates)
- Sibling subprojects' docs for cross-reference targets

Use the current detailed-eval date in the AI-attribution HTML block
(per convention 12) so the creation pass is dated and attributable.

Recent examples: dark_proteomes was created from 0 docs → 5 docs in commit
`e128e0b`; homolog_counts gained a missing subproject README + workflow
README in commit `4898c21`.

This is the doc-side counterpart to convention 44 (cross-check docs against code) —
when docs *don't exist*, the deep-eval pass owes a baseline doc set.

---

## 52. Sed-induced `RUN-workflow.sh` duplicate cleanup after convention 29 conversion

After bulk `sed -i 's|RUN-workflow\.sbatch|RUN-workflow.sh|g'` (per convention 29
unification), old dir trees and Key Files tables that previously listed
both files as adjacent rows now show two identical `RUN-workflow.sh`
lines. Detection pattern:

```bash
for f in $(find <subproject> -name '*.md' -not -path '*/x_*' -not -path '*/workflow-RUN_*'); do
  awk 'prev~/RUN-workflow\.sh/ && $0~/RUN-workflow\.sh/ {print FILENAME ":" NR ": " $0} {prev=$0}' "$f"
done
```

**Cleanup**: merge each duplicate pair into a **single** entry annotated
with `(local or SLURM via execution_mode YAML per convention 29)`. Do not delete
both — preserve the row so the file's existence is documented; just
collapse the duplicate.

Common dup contexts:
- Workflow `Key Files` tables: "Local runner" + "SLURM wrapper" rows
- Directory trees in BLOCK / subproject docs: adjacent `RUN-workflow.sh`
  + (formerly) `RUN-workflow.sbatch` lines

Established in gene_sizes (commit `ab6ad1b`).

---

## 53. Single-BLOCK subproject conda env naming — tolerated short form

convention 28 mandates `aiG-<subproject>-<block_or_step>` for per-BLOCK conda envs.
For **single-BLOCK subprojects**, the short form `aiG-<subproject>` is
tolerated (and currently in use), e.g.:

- `aiG-dark_proteomes` (one BLOCK: `BLOCK_classify_dark_proteome`)

Functional impact is zero (no naming collision possible when there's only
one BLOCK), and the short form is more legible in conda activation
commands. Doc this deviation in the subproject's README + BLOCK AI_GUIDE
so future readers know it's deliberate.

Stricter convention 28 form remains preferred for **multi-BLOCK** subprojects (e.g.,
`aiG-annotations_hmms-tmbed` — six tool BLOCKs, each with its own env).

If a single-BLOCK subproject grows a second BLOCK later, the short form
should be expanded to the strict convention 28 form at that time.

---

## 54. Bundled-payload accidental-commit followup-note protocol

When two parallel sessions (e.g., one in trees_gene_groups, one in
annotations_hmms) cause one session to inadvertently stage and commit the
other's in-progress work, **do not rewrite history**. Add a followup
commit:

- **Title**: `note: <hash> bundled an unintended payload`
- **Body**: explain what was bundled, confirm it's not destructive, link
  the two payloads from the commit title so future readers can untangle

Example: commit `7b05f62` (followup to `ad2c9cc`) — the STEP_2 SLURM
JobName change inadvertently swept in 14 file renames + 1 deletion from
the annotations_hmms in-progress session. The followup note documented
both payloads.

This avoids destructive history rewrites and produces a discoverable audit
trail. If the bundle WAS destructive (rather than just incomplete in the
title), the response would instead be a revert + redo — different protocol.

---

## 55. Untracking previously-tracked files in `research_user/`

convention 25 mandates that `research_notebook/research_user/` ships only
`.gitignore` (and `.gitkeep`-style markers). When deep-eval discovers
historic tracked content there (e.g., paper summaries committed before convention 25
was formalized, or migrated in from a per-subproject `research_notebook/`
where they were tracked):

- **`git rm --cached <file>`** — removes from index, keeps on disk
- File continues to live at the new (sandbox) path, gitignored
- Document the untracking in the commit message

Rationale: the convention 25 separation is the load-bearing rule that lets
`research_user/` stay completely free-form while GIGANTIC's
reproducibility guarantees remain intact. Tracked paper summaries violate
that separation. They can be re-tracked elsewhere later (a curated
literature index in `paper_preparation/` for example) if the user wants
them in the scientific record.

Example: gene_sizes commit `ab6ad1b` untracked two paper summaries
(mccoy_fire 2020, mccoy_fire 2024) from the migrated sandbox; the files
remain on disk under `research_user/subproject-gene_sizes/ai_research/`.

---

## 56. Workflow-level `README.md` is mandatory at every `workflow-COPYME-*/` root

Refines convention 35: every `workflow-COPYME-*/` directory ships BOTH:

- `README.md` at the workflow root — user-facing quick start + I/O
- `ai/AI_GUIDE.md` — AI-facing execution guide

When deep-eval encounters a workflow with only `ai/AI_GUIDE.md` and no
top-level `README.md`, create the README. Pattern: each workflow README
contains AI-attribution block + convention 42 Where-this-fits + Purpose + Usage
+ Inputs + Outputs + See-Also (pointer to `ai/AI_GUIDE.md`).

Example added: homolog_counts workflow README in commit `4898c21`.

---

## 57. Deep-eval per-subproject single-commit-per-subproject rhythm

The deep-eval sweep proceeds **one subproject at a time** with **one
commit + push per subproject** when working through multiple subprojects.
This gives a clean per-subproject changelog where each commit's diff
exactly covers one subproject's surface area.

Format of each commit message:
- **Title**: `<subproject>: <action> — bring to phylonames/genomesDB depth`
- **Body** sections:
  - Migration / structural changes (research_notebook, renames)
  - Bulk sed details
  - Doc enrichment (per-file changes)
  - Out-of-scope items explicitly listed
  - Stats line at end

Established 2026-05-26 across the 8-subproject sweep (annotations_hmms
`f763ba0` / dark_proteomes `e128e0b` / gene_sizes `ab6ad1b` /
homolog_counts `4898c21` / …).

Don't bundle multiple subprojects into one omnibus commit unless the user
explicitly asks (the omnibus pattern was used for trees_gene_families +
trees_gene_groups in commit `61ef05a`, but per-subproject is preferred
when working a list).

---

## 58. `x_*` gitignore pattern — archive-for-later-deletion

Parallels convention 49 `z_*` but with opposite intent:

| Prefix | Intent | Lifecycle |
|--------|--------|-----------|
| `x_*`  | Archive — staged for later deletion (was canonical, now superseded) | Past |
| `z_*`  | Early-development, not for general use yet                          | Future |

Both sort to the ends of alphabetical listings.

`x_*` is the simpler of the two: top-level gitignore pattern `x_*` ignores
files and dirs at any depth (basename match — no `**/` prefix needed).
No "keep README visible" exception — archived content is fully gitignored.

Used to set aside superseded code/templates/RUN dirs without deleting them
immediately, in case they're useful for reference or post-mortem. Eventually
deletable once nothing references them.

Pattern in root `.gitignore` (line 7):

```gitignore
x_*
```

Common occurrences:
- `x_workflow-COPYME-<old_design>-pre_<date>/` — superseded workflow templates
- `x_RUN-update_upload_to_server.sh-pre_helper_migration_<date>` — superseded scripts
- `x_<subproject>-archive-<date>/` — fully-retired subprojects

### When to use `x_` vs `z_`

| Situation | Use |
|-----------|-----|
| Past-canonical code being kept temporarily for reference, then deleted | `x_` |
| Brand-new code under development, not yet ready for general use | `z_` |
| Deprecated but might come back / unclear which direction | Default to `x_` (deprecation is the active framing) and rename to `z_` only if it does come back into active development |
| Work that is outside GIGANTIC and on neither track (permanent, not coming in, not going out) | neither — house it in the `zoo` subproject (convention 62) |

The two prefixes are NOT interchangeable — they signal opposite trajectories
in the lifecycle. `x_` says "going away," `z_` says "coming up."

---

## 59. GIGANTIC toolkits — optional NextFlow workflows for outside-subproject prep work

A **GIGANTIC toolkit** is a NextFlow workflow that users can **optionally**
run for work **outside** any gigantic subproject — typically to produce
inputs that gigantic subprojects then consume. Toolkits follow GIGANTIC
conventions the same way subprojects do, but are explicitly NOT
subprojects: their inputs are too variable across genome projects for the
framework to take ownership.

Per convention 60: toolkits **do not** become subprojects. They are a distinct,
permanent category of framework-shipped optional infrastructure.

### Why toolkits exist as a separate concept

Some prep work (e.g., downloading and processing public reference
genomes) is genuinely user-responsibility because the choices vary too
much from project to project to be standardized (which databases, which
assembly versions, which filters, which subsetting policy). But the same
prep work recurs across projects, so we ship working code as a reusable
starting point — a toolkit — rather than have every user reinvent it.

### Where toolkits live

Inside `research_notebook/research_ai/`, scoped to the downstream
subproject they feed:

```
gigantic_project-COPYME/research_notebook/research_ai/subproject-<X>/<toolkit_name>/
```

For example, the canonical seed toolkit:

```
gigantic_project-COPYME/research_notebook/research_ai/subproject-genomesDB/
└── ncbi_genomes-gigantic_T1_toolkit/
    ├── README.md
    ├── AI_GUIDE.md
    ├── output_to_input/                  # toolkit-stable view; symlinks into the current RUN's 3-output/
    │   ├── gene_annotations/
    │   ├── genomes/
    │   ├── maps/
    │   └── T1_proteomes/
    └── toolkit-COPYME-<descriptor>/      # the template (user copies + edits + runs)
        ├── ai/
        │   ├── AI_GUIDE.md
        │   ├── main.nf
        │   ├── nextflow.config
        │   ├── conda_environment.yml
        │   └── scripts/
        │       └── NNN_ai-<lang>-<descriptor>.<ext>
        ├── INPUT_user/
        │   ├── README.md
        │   └── <toolkit_manifest>.tsv
        ├── README.md
        ├── RUN-workflow.sh               # canonical convention 29 entry point
        └── START_HERE-user_config.yaml   # canonical convention 29 config name
```

User-copied run instances follow `toolkit-RUN_<N>-<descriptor>/` naming
(parallel extension of convention 35's `workflow-RUN_<N>-*` pattern). RUN
instances are gitignored by default (per convention 47 frozen-artifact rule) —
they exist only on the user's local machine after the run completes.

### Subproject-conformance is the rule, not the exception

Toolkits follow the same GIGANTIC conventions as subproject workflows.
There is no "relaxed-for-toolkits" set of rules — internally a toolkit
is built like a subproject workflow:

| Convention | How a toolkit applies it |
|---|---|
| convention 3 — `AI_GUIDE.md` naming | Plain `AI_GUIDE.md` at every level where one is needed |
| convention 12 — AI attribution headers | All toolkit-authored files |
| convention 17, convention 18 — INPUT_user staging arena | A toolkit's bridge step (commonly the next-to-last process) creates relative symlinks from `<project_root>/INPUT_user/<subdir>/` to the toolkit's outputs |
| convention 21 — Script naming | `NNN_ai-<lang>-<descriptor>.<ext>` |
| convention 23 — `${projectDir}` paths | Used throughout `main.nf` |
| convention 28 — Per-toolkit conda env | Own `conda_environment.yml`; env name `aiG-toolkit-<descriptor>` (convention 53 short-form OK for single-pipeline toolkits) |
| convention 29 — Unified `RUN-workflow.sh` + `START_HERE-user_config.yaml` | Canonical filenames, `execution_mode` YAML key, SLURM self-submit, COPYME guard |
| convention 34 — Self-documenting TSV headers | All toolkit-produced TSVs |
| convention 35 — Template vs RUN naming | `toolkit-COPYME-*` template / `toolkit-RUN_<N>-*` instance |
| convention 36 — Fail-fast | No `optional: true` outputs, `errorStrategy = 'terminate'`, `maxErrors = 0`, always-write outputs (empty-with-headers for legitimate empty cases) |
| convention 45 — `write_run_log` canonical final | Last script in every toolkit pipeline |
| convention 47 — Frozen RUN artifact | Do not edit completed `toolkit-RUN_<N>-*/` dirs; make forward fixes in the COPYME template |
| convention 56 — Workflow-level README.md | Mandatory at `toolkit-COPYME-*/` root |

The only places toolkit conventions diverge from subproject conventions:

1. **Location**: `research_notebook/research_ai/subproject-<X>/` instead
   of `subprojects/<X>/`. This signals that the framework does not own
   the inputs and never will.
2. **The bridge step**: toolkits include an explicit "bridge to
   `INPUT_user/`" process (commonly process N-1 of the pipeline) that
   creates relative symlinks from the project-level INPUT_user staging
   arena into the toolkit's `output_to_input/` view. Subproject
   workflows don't need this because downstream subprojects read their
   inputs from `output_to_input/` directly per convention 2.

### Gitignore behavior

Toolkits live in `research_notebook/research_ai/`, which default-ships
to GitHub. No special gitignore carve-out is required. Specifically:

- A toolkit's source files (`main.nf`, scripts, configs, READMEs,
  AI_GUIDEs, the COPYME template's `INPUT_user/` directory) all ship
  with the framework via the default `research_ai/` behavior.
- `x_*` archive subdirs inside a toolkit stay ignored per convention 58.
- `work/`, `.nextflow/`, `.nextflow.log*`, `OUTPUT_pipeline/`, and
  `toolkit-RUN_*/` instances stay ignored per the standard
  NextFlow-runtime + convention 47 frozen-artifact rules.

### Current toolkits

- **`subproject-genomesDB/ncbi_genomes-gigantic_T1_toolkit/`** —
  downloads NCBI RefSeq genome bundles (GCFs), T1-extracts proteomes
  with alternate-loci filtering, renames per GIGANTIC convention, and
  auto-bridges outputs into `INPUT_user/genomic_resources/{proteomes,
  genomes,annotations}/` for the genomesDB subproject to consume.

### See also

- convention 60 — GIGANTIC is consumed, not extended (framework posture toward
  user-added subprojects vs. shipped toolkits)
- convention 49 — `z_*` early-development counterpart
- convention 58 — `x_*` archive-for-later-deletion counterpart

---

## 60. GIGANTIC is consumed, not extended — user mods are expected; new user subprojects are out of scope

GIGANTIC is a framework users **consume**: they clone it, copy the
project template, and run the shipped subprojects on their data. They
do not build GIGANTIC itself.

Users will modify their copy wildly — adjusting scripts, configs,
workflow logic, even pipeline structure to fit their project. This is
expected and supported. The framework ships canonical, opinionated
defaults so the user has a sensible starting point; what they do from
there is their own.

If a user wants to **add a new subproject** (a new
`subprojects/<their_thing>/` with their own workflows, scripts, and
conventions), that is fine — but:

- It is **out of scope** for GIGANTIC framework guidance.
- It is **not** subject to GIGANTIC convention review or conformance.
- The shipped conventions remain available as reference if the user
  wants to mirror them, but the framework does not require this.

This is distinct from convention 59 (toolkits): toolkits are framework-shipped,
framework-owned, and conform to GIGANTIC conventions. User-added
subprojects are user-shipped, user-owned, and free of framework
expectations.

---

## 61. One chat session per subproject; root sessions at the named gigantic_project-COPYME

GIGANTIC's chat-as-research-notebook convention (convention 9) works best with
disciplined session hygiene. Two recommendations.

### Always root at the named gigantic_project-COPYME

Every chat session for project work should be initiated rooted at the
user's renamed copy of `gigantic_project-COPYME/` — e.g.,
`gigantic_project-cephalopod_evolution/`.

**Not** at:
- `GIGANTIC/` (the framework root, reserved for framework-development
  sessions per convention 16)
- `subprojects/<X>/` (a subproject directory)
- `subprojects/<X>/<BLOCK_or_STEP>/workflow-COPYME-*/` (a workflow directory)
- Any other directory deeper than the named project root

Why: the renamed project copy is the canonical session root. All
project conventions, INPUT_user paths, research_notebook captures,
and AI guidance are scoped to that directory. Rooting deeper than
that scopes the AI's view too narrowly and loses cross-subproject
context (and the AI guides at lower levels assume the session was
rooted above them). Rooting at `GIGANTIC/` is reserved for
framework-development sessions per convention 16.

### One chat session per subproject + a side channel for small questions

For productive project work:

- **One session per subproject** the user is actively working in. A
  session focused on `phylonames/` is different from one focused on
  `genomesDB/` is different from one focused on `trees_species/` —
  each maintains its own context, convention reminders, and recent
  state.
- **Continue the same session over many compactions** until it
  becomes overly reactive, muddled, or slow. Compactions are
  lossless (per convention 9 the full transcript is captured), so a long
  session isn't a problem until it starts feeling like one.
- **When a session goes muddled, start a fresh one** at the same
  named gigantic_project-COPYME root, focused on the same subproject,
  and bring it back up to speed (read the relevant AI_GUIDEs, recent
  commits, etc.).
- **A separate "small questions" session** for random or
  cross-cutting questions (e.g., "what does this convention mean?"
  or "is this NCBI accession a GCF or GCA?"). This keeps the
  subproject sessions focused on their actual work and prevents
  context pollution.

### What this prevents

- Sessions that try to hold every subproject's state in context and
  end up confused about which one they're operating on.
- Sessions that get derailed by one-off questions and lose their
  thread on the subproject work.
- Session captures (per convention 9) that mix multiple unrelated subprojects
  into a single transcript, making the lab-notebook record harder
  to grep later.

### See also

- convention 9 — chat-as-research-notebook lossless captures
- convention 16 — framework-development sessions are a separate scope (rooted
  at `GIGANTIC/`, distinct from project sessions)

---

## 62. `zoo` subproject — permanent holding pen for non-GIGANTIC work

`zoo` is a single subproject (`subprojects/zoo/`) that houses work which is
intentionally **outside GIGANTIC conventions** and is on **neither lifecycle
track** — not being incorporated in, not being phased out. It is the third
member of a three-way distinction with the convention 49 `z_*` and convention 58 `x_*` prefixes:

| Marker | Meaning | Trajectory |
|--------|---------|------------|
| `z_*`  | On track to eventually be **incorporated INTO** GIGANTIC | Coming up (future-canonical) |
| `x_*`  | Being **phased OUT of** GIGANTIC | Going away (archive) |
| `zoo`  | **Outside** GIGANTIC, on **neither** track — permanent holding pen ("where the wild things are") | Stays put |

Key properties:

- **Not a gitignore prefix.** Unlike `z_*`/`x_*`, `zoo` is an ordinary
  subproject directory: its non-data content (READMEs, scripts, configs) is
  tracked normally; only the usual per-subproject data is gitignored
  (`upload_to_server/*`, `OUTPUT_pipeline/`, etc.) exactly as for any
  subproject.
- **Sorts last** on both the command line and the data server — `zoo` sorts
  after even the `z_*` entries (`_` < `o`). Intentional.
- **One BLOCK per folded-in unit.** Each former standalone non-GIGANTIC
  subproject becomes one `BLOCK_<name>/`, moved **verbatim** (the analysis is
  unchanged — only its location). The shared `upload_to_server/` at the `zoo`
  root mirrors the blocks (`upload_to_server/BLOCK_<name>/...`), so the data
  server serves it via the single `zoo` allowlist entry.
- **Conventions caveat.** Contents may not follow GIGANTIC naming, vocabulary,
  manifest, or reproducibility conventions — that is the point. Do NOT flag
  `zoo` blocks as convention violations or propose migrating them onto
  templates (cf. convention 47 frozen-artifact rule).

First instance (2026-06-28): the former standalone `leonid_requests` and
`moroz_innovations` subprojects (ad-hoc Leonid Moroz delivery + an
innovation-vocabulary test run) were folded in as `zoo/BLOCK_leonid_requests`
and `zoo/BLOCK_moroz_innovations`, and removed from `subprojects/` root.

### See also

- convention 49 — `z_*` early-development ("coming up") counterpart
- convention 58 — `x_*` archive-for-later-deletion ("going away") counterpart

---

## 63. `pkill -f` self-match footgun — use the `[g]` bracket trick

When stopping a process by command-line pattern with `pkill -f <name>` from a
**scripted or remote (ssh) shell**, the killing shell's *own* command line
contains `<name>` (it appears in the `pkill` argument), so `pkill -f` matches
and kills that shell too — often mid-script, before later commands run. The
classic symptom: the target is killed, the restart step never executes, and
no error or logfile appears. Silent.

Fix: wrap the first character in a character class so the regex still matches
the target but not the literal pattern in the killing shell's argv:

```bash
pkill -f '[g]igantic_server.py'   # matches the server; the killing shell's
                                  # argv has "[g]igantic_server.py", which the
                                  # regex does not match
```

Canonical instance: the GIGANTIC data-server restart commands in
`server/Login-node-server-GUIDE.md` (Step 1 and the quick-restart one-liner).
A plain `pkill -f gigantic_server.py` there took the server down without
restarting it (hit 2026-06-28).

---

## 64. No invented acronyms or abbreviations in user-facing communication

convention 32 governs abbreviations in **code** (full words — `sequence_count` not
`seq_cnt`; established scientific abbreviations like GO / Pfam / BLAST kept
as-is). This section extends the same discipline to **prose**: chat
messages, commit messages, READMEs, AI_GUIDEs, and any text a human reads.

**Rule**: never coin an acronym or abbreviation for a name (subproject,
BLOCK, STEP, file, concept). Write every name out in full, every time —
`one_direction_homologs`, not "ODH"; `annogroups`, not "AG";
`trees_gene_families`, not "TGF".

The only abbreviations allowed in prose are:

- ones the **user introduced first** (mirror their shorthand), and
- established scientific abbreviations per convention 32 (GO, Pfam, BLAST, NCBI nr, …).

**Why**: the user reads these messages directly and manages the project
from them. A made-up acronym forces them to decode it, and a single
ambiguous token (e.g. "ODH" for `one_direction_homologs`) can derail a
conversation. The cost of writing the full name is trivial; the cost of a
misread name is not.

---

## 65. Dual-layer output timestamps (GIGANTIC v2.0 — **pilot in progress**, July 2026)

**Status**: **Pilot implementation underway** in `integrator/` (all six blocks)
and `sequence_groups_X_species/`. Full project-wide rollout remains v2.0;
see `GIGANTIC_v2.0_TODO.md`. v1.0 subprojects outside the pilot still use
stable filenames only.

**Problem**: Researchers browsing the data server (e.g. Leonid Moroz) benefit
from **run-date stamps in output filenames** so they can compare runs and
know when data were produced. Pipelines that read **hardcoded paths** or
symlink basenames that change every run would **break**.

**Solution — dual layer** (human/server vs machine):

| Layer | Location | Filename | Consumers |
|-------|----------|----------|-----------|
| **Archival / server** | `OUTPUT_pipeline/` inside `workflow-RUN_N-*`; published under `upload_to_server/` | Includes runtime suffix, e.g. `_july11_1645` | Humans, server browsing, run archive |
| **Machine interface** | `<subproject>/output_to_input/` | **Stable** — no date suffix | Downstream `START_HERE-user_config.yaml`, manifests, scripts |

**Example**:

```
OUTPUT_pipeline/species70_X_orthogroups/4-output/
  4_ai-species70_X_orthogroups-composite_clades-per_group_july11_2145.tsv   ← real file

output_to_input/orthogroups/species70_X_orthogroups/
  4_ai-species70_X_orthogroups-composite_clades-per_group.tsv             ← stable symlink
    → points at the timestamped file above
```

**Rules (v2.0)**:

1. **Never** put timestamped paths in `START_HERE-user_config.yaml` or
   inter-subproject configs — always read from `output_to_input/`.
2. **`RUN-workflow.sh`** (or equivalent publisher) must create symlinks with
   **fixed alias names** (strip the runtime suffix), not `basename "$f"` of
   the timestamped file.
3. **`upload_manifest.tsv`** globs must remain compatible (e.g.
   `4_ai-*-composite_clades-per_group*.tsv`) or use explicit `dest_name`.
4. **Within a single workflow run**, scripts that depend on each other's
   outputs use a **pointer file** (integrator v1.0 precedent:
   `1-output/_shared/1_ai-run_timestamp_suffix.txt`) or pass the suffix
   through NextFlow params — do not guess filenames.
5. **Shared helper**: centralize `filename_timestamp_suffix()` (format
   `_<monthname><day>_<hhmm>`, e.g. `_july11_1645`) in a project-wide
   utility (extend `integrator/ai/utils_integrator_shared.py` or a new
   `gigantic_output_conventions` module).
6. **Rollout**: phased by tier — not big-bang. Pilot on server-facing
   subprojects first (`sequence_groups_X_species`, integrator catalog
   blocks). **Do not** timestamp internal intermediates (BLAST reports,
   membership build internals) unless the same run uses a pointer file.

**v1.0 partial precedent** (now extended by pilot): integrator blocks and
`sequence_groups_X_species` use `OUTPUT_pipeline/1_ai-run_timestamp_suffix.txt`
(written by `RUN-workflow.sh` before NextFlow), timestamped archival files, and
stable `output_to_input/` symlinks via `integrator/ai/link_stable_output_to_input_symlinks.py`.

**v1.0 everywhere else**: stable filenames only; run provenance from
`workflow-RUN_N-*` directory names and Script 005 / `write_run_log`
timestamped logs in `ai/logs/` (convention 45).

---

<!-- Add new conventions below as they surface during per-directory review. -->
<!-- User shorthand "gcon" = "please add this to gigantic_conventions.md". -->

