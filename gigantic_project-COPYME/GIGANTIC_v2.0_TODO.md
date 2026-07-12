# GIGANTIC v2.0 — Planned work (not v1.0)

**AI**: Claude (Cursor) | Opus 4.8 | 2026 July 11  
**Human**: Eric Edsinger

v1.0 ships with **stable output filenames**. Items below are **deferred to
v2.0** so the v1.0 release is not destabilized by cross-cutting refactors.

**Canonical convention**: convention 65 in `ai/ai_FYIs/gigantic_conventions.md`

**Repo-root copy**: `../GIGANTIC_v2.0_TODO.md` (same checklist; keep in sync
when editing either file).

---

## Dual-layer output timestamps (project-wide)

**Goal**: Run-date stamps in filenames for **server / human** browsing, while
**pipelines** keep reading **stable paths** under `output_to_input/`.

### Implementation checklist (v2.0)

- [x] Add shared `filename_timestamp_suffix()` + pointer read/write to
      `integrator/ai/utils_integrator_shared.py` (+ `write_workflow_run_timestamp.py`)
- [x] Add `link_stable_output_to_input_symlinks.py` (stable alias symlinks;
      `--strip-stage-prefix` for integrator layouts)
- [x] **Pilot** `sequence_groups_X_species` — COPYME scripts 001–006 + RUN-workflow.sh
- [x] **Pilot** integrator — all six COPYME blocks (timestamps + RUN linker)
- [ ] Create and validate `workflow-RUN_6-sequence_groups` (timestamp pilot run) — **submitted** SLURM 36883425
- [ ] Create integrator pilot RUN(s) and verify stable `output_to_input/` aliases — **in flight** (see below)
- [ ] Audit all `upload_manifest.tsv` glob patterns for suffix compatibility
- [ ] Document rule in each subproject AI_GUIDE: **no timestamped paths in YAML configs**
- [ ] Phased rollout to other server-facing subprojects (tiered — not big-bang)
- [ ] Explicit **exclude list**: internal intermediates (BLAST, per-step scratch)
      unless pointer-file pattern is in place

### v1.0 state (unchanged outside pilot)

- Non-pilot subprojects: stable filenames; provenance via `workflow-RUN_N-*`
  and `ai/logs/run_*` (convention 45)

---

<!-- Add additional v2.0 items below as they are parked from v1.0 sessions. -->
