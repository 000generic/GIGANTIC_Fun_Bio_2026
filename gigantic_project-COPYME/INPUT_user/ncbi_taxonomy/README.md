<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: Provenance for the pinned NCBI taxonomy snapshot used by phylonames.
============================================================================ -->

# Pinned NCBI Taxonomy Snapshot

This directory holds a **fixed NCBI `new_taxdump` snapshot** so the
`phylonames` subproject can regenerate phylonames **reproducibly** — pinning
one snapshot guarantees the GIGANTIC-generated numbered unknown clades
(e.g. `Kingdom6555`) and all phylonames are identical across re-runs.

## How to use it

In `phylonames/STEP_1-generate_and_evaluate/workflow-*/START_HERE-user_config.yaml`:

```yaml
ncbi_taxonomy:
  source_mode: "supply_path"
  taxonomy_path: "../../../../INPUT_user/ncbi_taxonomy/database-ncbi_taxonomy_latest"
```

`database-ncbi_taxonomy_latest` is a symlink to the dated snapshot directory
below. STEP_1 script `002` reads `<snapshot>/rankedlineage.dmp`.

## Contents

```
database-ncbi_taxonomy_20260421_005529/   # the pinned snapshot (15 .dmp files + download_metadata.txt)
database-ncbi_taxonomy_latest -> database-ncbi_taxonomy_20260421_005529
```

## Provenance

- **Snapshot:** `database-ncbi_taxonomy_20260421_005529`
- **Source:** `ftp://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.tar.gz`
- **Downloaded:** 2026-04-20 20:55 EDT (2026-04-21 00:55 UTC)
- **Original archive md5:** `53f1f23a711d4b69e76cb7d15d170e67` (new_taxdump.tar.gz)
- **rankedlineage.dmp md5:** `41f9e2c3ae29582695867a648af34d5b`
- **Origin:** This is the exact snapshot that generated the project's current
  `species70` phylonames mapping. It was preserved here (2026-06-28) from the
  NextFlow `work/` cache of
  `STEP_1-generate_and_evaluate/workflow-RUN_1-generate_phylonames/` so the
  mapping can be reproduced and the full phylonames list regenerated without
  re-downloading (which could shift numbered clades).

Do not delete or replace this snapshot without understanding that re-running
phylonames against a different snapshot can change assigned phylonames and
break downstream subprojects that already key on them.
