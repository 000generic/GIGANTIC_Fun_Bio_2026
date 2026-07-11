# AI Guide: BLOCK_secretome_per_moroz_17may2026

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 21 (initial scoping)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — secretome overview + full Moroz spec detail
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-secretome_per_moroz_17may2026/`](workflow-COPYME-secretome_per_moroz_17may2026/)
- This BLOCK's workflow guide: [`workflow-COPYME-secretome_per_moroz_17may2026/ai/AI_GUIDE.md`](workflow-COPYME-secretome_per_moroz_17may2026/ai/AI_GUIDE.md)
- Reads FROM (per Moroz spec, when scripted):
  - `../../annotations_hmms/output_to_input/BLOCK_signalp/` (SignalP6 — `Sec/SPI` only as KEEPER)
  - `../../annotations_hmms/output_to_input/BLOCK_deeploc/` (DeepLoc 2.0 — TM + Extracellular probabilities)
  - `../../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/` (Pfam domains)
- Outputs TO: `../output_to_input/BLOCK_secretome_per_moroz_17may2026/` (when scripted)
- 0 scripts (scaffold only; awaiting upstream SignalP refresh)
- Conda env: `aiG-secretome-secretome_per_moroz_17may2026`

---

## Status — SCAFFOLD ONLY

This BLOCK is a separate (orthogonal) implementation track to the
`STEP_1-build_evidence_table` + `STEP_2-filter_secretome` chain.
It implements the Moroz lab spec (2026-05-17) directly as a sequence
of KEEPER/DROPPER filters per the spec's pipeline.

**Currently has zero scripts** — awaiting fresh SignalP6 output from
annotations_hmms on species70 (previous run produced only 2/70 species).
See the subproject AI_GUIDE for the full upstream-data table + decision
log captured 2026-05-20/21.

## Pipeline (per Moroz spec — to be scripted when SignalP refresh lands)

Sequential KEEPER/DROPPER filters. Each script's KEEPER output is the
next script's input:

| # | Script | Filter | KEEPER | DROPPER |
|---|--------|--------|--------|---------|
| 001 | SignalP6 signal peptide | `Sec/SPI` only (classical secretory) | has SignalP6 `Sec/SPI` | no SignalP OR `Sec/SPII` OR `Tat/SPI` |
| 002 | DeepLoc TM / localization | replaces originally-spec'd TMBed | low TM AND/OR high Extracellular | high TM OR localized elsewhere |
| 003 | Pfam domain composition (strict) | unchanged from spec | (uniq=1 AND total≤4) OR (uniq=2 AND total=2) | everything else |
| 004–010 | TBD | — | — | — |

## Open Questions (per subproject AI_GUIDE, revisit when scripting resumes)

1. DeepLoc probability thresholds (Transmembrane, Extracellular)
2. SignalP `SP_Probability` anomaly (verify on fresh run)
3. DeepLoc `Signals` column overlap with SignalP6
4. Pfam multi-hit overlap counting rule

## Relationship to the other secretome units

- This BLOCK implements the Moroz spec **directly** via per-script filters.
- The sibling `STEP_1-build_evidence_table` + `STEP_2-filter_secretome`
  chain implements an **evidence-table-first** approach: pivot all annotation
  evidence to wide tables, then apply user-defined filter manifests.
- Both approaches are kept; the user will compare results once both are
  fully implemented.

## See Also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — subproject AI guide with the FULL Moroz spec detail (pipeline logic, decision log, upstream-data table)
- [`workflow-COPYME-secretome_per_moroz_17may2026/README.md`](workflow-COPYME-secretome_per_moroz_17may2026/README.md) — workflow usage (scaffold)
- [`workflow-COPYME-secretome_per_moroz_17may2026/ai/AI_GUIDE.md`](workflow-COPYME-secretome_per_moroz_17may2026/ai/AI_GUIDE.md) — workflow execution
