# INPUT_user — composite clades manifest

This directory holds the one user-curated input for the workflow:

**`composite_clades_manifest.tsv`** — the list of composite clades to report
(Script 004). Each row picks one ALGORITHM and the clades it applies to:

| Algorithm | Question it asks of a group's member species | Naming |
|---|---|---|
| `exact` | members come from EXACTLY the listed component clades | auto: `cc_<components>-exact` |
| `absent` | members are ABSENT from ALL the listed clades | auto: `cc_<clades>-absent` |
| `core_urclade` | members in an OUTGROUP of the target AND in an ingroup (the target's Ur = last-common-ancestor core) | user-named: `cc_<Name>-core_urclade` |
| `core_early_clade` | members in two or more ingroups (the target's Early window = early descendant branches / the species tree's ambiguous nodes) | user-named: `cc_<Name>-core_early_clade` |

Columns (tab-separated; `#` comments): `Algorithm  Name  Target_Clade  Clades`.
`exact`/`absent` are deterministic (no Name needed); `core_*` are user-named. The
clade names you reference (e.g. `Ctenophora`, `Bilateria`, `Metazoa`) are the GROUP
names + the scope name defined in `START_HERE-user_config.yaml`'s `composite_clades`
block, or any `C###_Name` clade id from the clade mappings.

The default manifest mirrors the metazoan composite clades used across GIGANTIC
(the five clades Ctenophora / Porifera / Placozoa / Cnidaria / Bilateria within
Metazoa, plus NonMetazoa). Edit it to ask different questions; nothing else changes.
