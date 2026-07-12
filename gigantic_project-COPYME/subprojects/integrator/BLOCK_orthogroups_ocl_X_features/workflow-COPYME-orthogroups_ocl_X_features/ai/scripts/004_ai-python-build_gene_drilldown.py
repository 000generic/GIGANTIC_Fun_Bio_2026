#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Build the per-structure gene-level integration drill-down (Table 3)
# Human: Eric Edsinger

"""
Script 004 — Gene-level drill-down (Table 3), per structure.

One row per (orthogroup, member gene): the gene's dark / hotspot / secretome
status plus the secretome evidence columns (SignalP / DeepLoc / Pfam), carrying
the orthogroup's OCL origin block + state for context. Lets a user trace any
single member gene.

Inputs:
  - OCL summary (<ocl_orthogroups_dir>/structure_NNN/
      4_ai-orthogroups-complete_ocl_summary.tsv) for orthogroup -> members +
      origin block/state.
  - Feature lookup (Script 001) for each member's per-gene features + evidence.

Members absent from the lookup are still emitted, with availability flags NA
(union + flags policy — never silently dropped). One row per (orthogroup,
member gene). Fail-fast: exits 1 on missing inputs.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U

# Lookup columns carried into the drill-down (by self-documenting header_ID).
LOOKUP_FEATURE_COLUMNS = [
    "Dark_Available",
    "Is_Dark",
    "Hotspot_Available",
    "In_Hotspot",
    "Hotspot_ID",
    "Secretome_Available",
    "Is_Secreted",
    "SignalP_Call",
    "SignalP_Probability",
    "DeepLoc_Extracellular_Probability",
    "DeepLoc_Transmembrane_Probability",
    "Pfam_Unique_Accessions",
    "Pfam_Total_Hits",
]


def load_feature_lookup_full( lookup_path: Path ) -> dict:
    """full_id -> { feature_column : value } for the LOOKUP_FEATURE_COLUMNS."""
    full_ids___features = {}
    with open( lookup_path, 'r' ) as input_lookup:
        # Full_GIGANTIC_Gene_ID (...)\tGenus_Species (...)\tSource_Gene_Field (...)\tDark_Available (...)\t...
        # g_A1BG-...\tHomo_sapiens\tA1BG\tTrue\t...
        header_line = input_lookup.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_full_id = header_ids___indices[ "Full_GIGANTIC_Gene_ID" ]
        feature___indices = { col: header_ids___indices[ col ] for col in LOOKUP_FEATURE_COLUMNS }
        for line in input_lookup:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            full_ids___features[ parts[ index_full_id ] ] = {
                col: ( parts[ idx ] if idx < len( parts ) else "" )
                for col, idx in feature___indices.items()
            }
    return full_ids___features


def main():
    parser = argparse.ArgumentParser( description = "Build gene-level drill-down (Table 3)" )
    parser.add_argument( '--structure_id', required = True )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    structure_id = args.structure_id
    structure_name = f"structure_{structure_id}"

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    input_ocl_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "ocl_orthogroups_dir" ] )

    input_ocl_summary_path = input_ocl_dir / structure_name / "4_ai-orthogroups-complete_ocl_summary.tsv"
    output_base = Path( args.output_dir )
    input_lookup_path = U.resolve_timestamped_output_path(
        output_base / "_shared" / "1-output", "1_ai-gene_feature_lookup", output_base )

    if not input_ocl_summary_path.is_file():
        print( f"CRITICAL ERROR: OCL summary not found: {input_ocl_summary_path}", file = sys.stderr )
        sys.exit( 1 )
    if not input_lookup_path.is_file():
        print( f"CRITICAL ERROR: feature lookup not found: {input_lookup_path}", file = sys.stderr )
        print( "  Script 001 (build_feature_lookup) must run before this script.", file = sys.stderr )
        sys.exit( 1 )

    full_ids___features = load_feature_lookup_full( input_lookup_path )
    print( f"[004 {structure_name}] loaded {len( full_ids___features )} gene feature rows" )

    output_dir = Path( args.output_dir ) / structure_name / "4-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_drilldown_path = U.timestamped_output_path( output_dir, "4_ai-genes-integrated_drilldown", output_base )

    header_columns = [
        "Structure_ID (phylogenetic species tree structure identifier)",
        "Orthogroup_ID (orthogroup identifier from OCL analysis)",
        "Origin_Phylogenetic_Block (phylogenetic block where the orthogroup originated Parent_Clade_ID_Name::Child_Clade_ID_Name)",
        "Origin_Phylogenetic_Block_State (origin block in five-state vocabulary with O marking Origin)",
        "Sequence_ID (member GIGANTIC sequence identifier)",
        "Genus_Species (Genus_species parsed from the sequence identifier phyloname)",
        "Source_Gene_Field (bare gene field parsed from the g_ prefix)",
        "Dark_Available (True if the gene's species had a dark_proteome classification)",
        "Is_Dark (True if dark; False if annotated; NA if species not available)",
        "Hotspot_Available (True if the gene's species had a hotspots analysis)",
        "In_Hotspot (True if the gene is in a hotspot; False otherwise; NA if not available)",
        "Hotspot_ID (hotspot identifier the gene belongs to; empty if none; NA if not available)",
        "Secretome_Available (True if the gene's species had a filtered secretome)",
        "Is_Secreted (True if in the filtered secretome; False otherwise; NA if not available)",
        "SignalP_Call (signalp_fast Call from secretome evidence; empty if none)",
        "SignalP_Probability (signalp_fast Probability from secretome evidence; empty if none)",
        "DeepLoc_Extracellular_Probability (deeploc Extracellular probability from secretome evidence; empty if none)",
        "DeepLoc_Transmembrane_Probability (deeploc Transmembrane probability from secretome evidence; empty if none)",
        "Pfam_Unique_Accessions (pfam unique annotation count from secretome evidence; empty if none)",
        "Pfam_Total_Hits (pfam total hit count from secretome evidence; empty if none)",
    ]

    def na_features():
        # Member not in lookup: every axis NA / empty (still emitted).
        return { col: ( "NA" if col in ( "Dark_Available", "Is_Dark", "Hotspot_Available",
                                          "In_Hotspot", "Hotspot_ID", "Secretome_Available",
                                          "Is_Secreted" ) else "" )
                 for col in LOOKUP_FEATURE_COLUMNS }

    gene_row_count = 0
    with open( input_ocl_summary_path, 'r' ) as input_ocl_summary, \
         open( output_drilldown_path, 'w' ) as output_drilldown:
        output_drilldown.write( '\t'.join( header_columns ) + '\n' )

        # Orthogroup_ID (...)\tOrigin_Phylogenetic_Block (...)\tOrigin_Phylogenetic_Block_State (...)\t...\tSequence_IDs (comma delimited ...)
        # OG000000\tC000_OOL::C071_Basal\tC000_OOL::C071_Basal-O\t...\tg_10255c0g2-...,g_13896c2g2-...
        header_line = input_ocl_summary.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_origin_block = header_ids___indices[ "Origin_Phylogenetic_Block" ]
        index_origin_state = header_ids___indices[ "Origin_Phylogenetic_Block_State" ]
        index_sequence_ids = header_ids___indices[ "Sequence_IDs" ]

        for line in input_ocl_summary:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ index_og ]
            origin_block = parts[ index_origin_block ]
            origin_state = parts[ index_origin_state ]
            sequence_ids_cell = parts[ index_sequence_ids ] if index_sequence_ids < len( parts ) else ""
            members = [ m for m in sequence_ids_cell.split( ',' ) if m ]

            for member in members:
                source_gene_field, phyloname, genus_species = U.parse_full_gigantic_id( member )
                features = full_ids___features.get( member, na_features() )
                output = '\t'.join( [
                    structure_id,
                    orthogroup_id,
                    origin_block,
                    origin_state,
                    member,
                    genus_species if genus_species is not None else "",
                    source_gene_field if source_gene_field is not None else "",
                ] + [ features[ col ] for col in LOOKUP_FEATURE_COLUMNS ] ) + '\n'
                output_drilldown.write( output )
                gene_row_count += 1

    print( f"[004 {structure_name}] wrote {gene_row_count} gene rows -> {output_drilldown_path}" )


if __name__ == '__main__':
    main()
