# homolog_counts — Server Files

Per-species70 homolog count tables, one wide TSV per upstream source.

## Layout

This directory is built automatically by the subproject-root
`RUN-update_upload_to_server.sh`, which calls the shared helper
`server/ai/update_upload_to_server.py`. It reads the per-workflow
`upload_manifest.tsv` from the most recent `workflow-RUN_*` and publishes the
files (as symlinks) into a nested tree that mirrors the source:

```
upload_to_server/BLOCK_homolog_counts/workflow-RUN_<K>-homolog_counts/<N>-output/<file>
```

Only the newest RUN per block is published; superseded runs are pruned. Do not
hand-edit symlinks here — rerun `RUN-update_upload_to_server.sh` instead. The
file inventory and per-file descriptions below are the published deliverables.

## Files

| File | Rows | Description |
|---|---|---|
| `1_ai-species70_alphabetical_phylonames.tsv` | 70 | Canonical alphabetical phyloname column order shared by all count tables below |
| `2_ai-counts-orthogroups_orthohmm.tsv` | 202,994 | Orthogroup counts per species, from the canonical `orthogroups/BLOCK_orthohmm_GIGANTIC` (`gene_count_gigantic_ids.tsv` re-keyed and summarized) |
| `3_ai-counts-trees_gene_groups.tsv` | 1,974 | HGNC gene group homolog counts per species, from `trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/STEP_1-homolog_discovery/`. **Additive** counting across RGS reference sequences and `>g_` BLAST-discovered homologs. |
| `4_ai-counts-trees_gene_families.tsv` | 76 | Curated gene family homolog counts per species, from `trees_gene_families/output_to_input/<family>/STEP_1-homolog_discovery/`. **Additive** counting across RGS and `>g_`. |
| `5_ai-run_log.md` | — | Timestamped record of the workflow run that produced these tables |
| `6_ai-counts-orthogroups_orthohmm-short_species_headers.tsv` | 202,994 | Same data as file 2, with the 70 species column headers shortened to `<Phylum-or-clade> <Genus> <species>` |
| `7_ai-counts-trees_gene_groups-short_species_headers.tsv` | 1,974 | Same data as file 3, with short species column headers |
| `8_ai-counts-trees_gene_families-short_species_headers.tsv` | 76 | Same data as file 4, with short species column headers |

## Short species column header rule (files 6, 7, 8)

For **metazoan** species (phyloname starting with `Metazoa_`): `Phylum Genus species` — e.g., `Chordata Homo sapiens`, `Cnidaria Hydra vulgaris`.

For **non-metazoan** species: `<first non-digit clade> Genus species`. The clade is the first underscore-separated field at position 0–4 (Kingdom/Phylum/Class/Order/Family) that contains no digit characters. Examples:
- `Ichthyosporea Abeoforma whisleri` (Class is the first non-digit; Kingdom and Phylum have digit-placeholders)
- `Choanoflagellata Monosiga brevicollis_MX1` (Class)
- `Filasterea Capsaspora owczarzaki` (Class)
- `Rotosphaerida Parvularia atlantis` (Order; Kingdom, Phylum, and Class all have digit-placeholders)

**Edge-case resolution (May 2026)**: Three species whose entries in the species70 phyloname manifest are stale and uninformative (`Kingdom21801…` or `NOTINNCBI×5_…`) get direct short-label overrides in script 006 using user-chosen specific clades:
- **`Filozoa Corallochytrium limacisporum`**
- **`Ichthyosporea Chromosphaera perkinsii`** (Class; same level as the other 4 Ichthyosporea entries — Abeoforma, Creolimax, Sphaeroforma, Ichthyophonus)
- **`Placozoa Hoilungia hongkongensis_H13`** (metazoan Phylum)

Files 2/3/4 (with full phyloname headers) and files 6/7/8 (with short labels) contain **identical numeric data** in identical column order. Choose whichever set is easier to read.

## Table schema (files 2, 3, 4 and their short-header counterparts 6, 7, 8)

All count tables share an identical column structure:

| # | Column | Description |
|---|---|---|
| 1 | `Feature_ID` | Orthogroup ID (file 2/6) / gene group name (file 3/7) / gene family name (file 4/8) |
| 2 | `Total_Count` | Sum of homolog counts across all 70 species |
| 3 | `Total_Species_Count` | Number of species with at least 1 homolog |
| 4–73 | per-species count | 70 columns ordered alphabetically by phyloname; column header is the full phyloname in files 2/3/4, or the short `<clade> <Genus> <species>` label in files 6/7/8 |
| 74 | `Human_Gene_Names_List` | semicolon-delimited list of human gene names (HGNC symbols / NCBI gene names) found in this row. Dedupd. |
| 75 | `Ctenophore_Sequence_IDs_List` | semicolon-delimited list of gene_id values from ctenophore species (Beroe_ovata, Hormiphora_californensis, Pleurobrachia_bachei, Bolinopsis_microptera, Mnemiopsis_leidyi) |
| 76 | `Sponge_Sequence_IDs_List` | semicolon-delimited list of gene_id values from sponge species (Sycon_ciliatum, Chondrosia_reniformis, Dysidea_avara, Ephydatia_muelleri, Halichondria_panicea, Oscarella_lobularis, Corticium_candelabrum) |
| 77 | `Placozoan_Sequence_IDs_List` | semicolon-delimited list of gene_id values from placozoan species (Cladtertia_collaboinventa, Trichoplax_adhaerens, Trichoplax_sp_H2, Hoilungia_hongkongensis_H13) |
| 78 | `Cnidarian_Sequence_IDs_List` | semicolon-delimited list of gene_id values from cnidarian species (Nematostella_vectensis, Acropora_muricata, Pocillopora_verrucosa, Hydractinia_symbiolongicarpus, Hydra_vulgaris) |

Gene IDs in columns 75-78 are parsed from `>g_<gene_id>-t_<transcript>-p_<protein>-n_<phyloname>` FASTA headers (or equivalent tokens in the orthohmm membership file). `<gene_id>` is the field immediately after `g_` and before `-t_`.

## Known caveats (May 2026)

**RGS/BLAST duplication in upstream AGS files**: The `trees_gene_groups` and `trees_gene_families` upstream STEP_1 AGS FASTA files currently emit every curated reference protein TWICE — once as an `>rgs_` header and once as a `>g_*-<species>` BLAST self-hit. Until that upstream bug is fixed, counts in files 3 and 4 are inflated for species whose proteins also appear in the curated reference set (primarily Homo_sapiens, plus Drosophila_melanogaster / Caenorhabditis_elegans for `kinases_*`, `phosphatases_*`, `innexin_pannexin_channels`, and `transient_receptor_potential_cation_channels` in file 4). File 2 (orthogroups) is unaffected.

**Phyloname format substitutions**: The species70 manifest uses up-to-date phylonames for all 70 species. Some upstream FASTA `-n_<phyloname>` suffixes still use an older phylonames-registry version (15 species in `trees_gene_groups`, same 15 in `trees_gene_families`). Counting scripts match on `genus_species` (parts[5:] of the phyloname) and write the manifest phyloname in output column headers, so the column labels are consistent across all tables. Per-substitution counts are logged in the per-script `*-log-*.log` files.

**RGS organisms not in species70**: One mouse (Mus_musculus) and one anemone RGS were skipped in file 4 (no species70 mapping). Documented in `4_ai-log-count-trees_gene_families.log`.
