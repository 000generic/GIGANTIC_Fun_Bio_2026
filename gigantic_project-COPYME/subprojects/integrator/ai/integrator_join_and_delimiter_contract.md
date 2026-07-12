# Integrator join and delimiter contract

**Code**: `integrator/ai/utils_integrator_shared.py`

| Level | Rule | Constant |
|-------|------|----------|
| Between columns | Tab | TSV |
| Within column — lists | Comma | `DELIM` |
| Within column — composite text | Semicolon | `SUBDELIM` |
| Within column — names | ` // ` | `NAME_DELIM` |
| Missing value | `NA` | `NA` |

**Join keys**: full GIGANTIC sequence ID (most features); hotspots use `(Genus_species, bare g_ field)`; gene groups use HGNC `Gene_Group_ID` (`gg<N>`).

**Aligned subprojects**: `sequence_groups_X_species` imports this module for delimiter and gene-group helpers.
