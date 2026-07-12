#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Build the per-structure integrated orthogroup summary (Table 1)
# Human: Eric Edsinger

"""
Script 002 — Integrated orthogroup summary (Table 1), per structure.

Spine: the OCL orthogroup summary for this structure
  (<ocl_orthogroups_dir>/structure_NNN/4_ai-orthogroups-complete_ocl_summary.tsv).
Each orthogroup row carries Sequence_IDs (member GIGANTIC IDs). For each member
we look up dark/hotspot/secretome membership in the structure-invariant feature
lookup (built by Script 001) and aggregate to the orthogroup:

  - a count of integration with each source
  - the member sequence IDs that integrate with each source (list-cell)
  - an availability count per source (members whose species had that source) so
    the count's denominator is transparent (union + flags policy)

One row per (structure, orthogroup). In-column lists use bare commas (§34).
Fail-fast: exits 1 if the OCL summary or the feature lookup is missing.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U


def load_feature_lookup( lookup_path: Path ) -> dict:
    """full_id -> ( is_dark, in_hotspot, is_secreted, dark_avail, hotspot_avail, secretome_avail )."""
    full_ids___features = {}
    with open( lookup_path, 'r' ) as input_lookup:
        # Full_GIGANTIC_Gene_ID (...)\tGenus_Species (...)\t...\tIs_Dark (...)\t...\tIn_Hotspot (...)\t...\tIs_Secreted (...)\t...
        # g_A1BG-...\tHomo_sapiens\t...\tFalse\t...\tFalse\t...\tFalse\t...
        header_line = input_lookup.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_full_id = header_ids___indices[ "Full_GIGANTIC_Gene_ID" ]
        index_is_dark = header_ids___indices[ "Is_Dark" ]
        index_in_hotspot = header_ids___indices[ "In_Hotspot" ]
        index_is_secreted = header_ids___indices[ "Is_Secreted" ]
        index_dark_avail = header_ids___indices[ "Dark_Available" ]
        index_hotspot_avail = header_ids___indices[ "Hotspot_Available" ]
        index_secretome_avail = header_ids___indices[ "Secretome_Available" ]
        for line in input_lookup:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            full_ids___features[ parts[ index_full_id ] ] = (
                parts[ index_is_dark ],
                parts[ index_in_hotspot ],
                parts[ index_is_secreted ],
                parts[ index_dark_avail ],
                parts[ index_hotspot_avail ],
                parts[ index_secretome_avail ],
            )
    return full_ids___features


def main():
    parser = argparse.ArgumentParser( description = "Build integrated orthogroup summary (Table 1)" )
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
        print( f"CRITICAL ERROR: OCL summary not found for {structure_name}", file = sys.stderr )
        print( f"  Expected: {input_ocl_summary_path}", file = sys.stderr )
        print( "  Verify ocl_orthogroups_dir exposes this structure (run_label + structure_id).", file = sys.stderr )
        sys.exit( 1 )
    if not input_lookup_path.is_file():
        print( f"CRITICAL ERROR: feature lookup not found: {input_lookup_path}", file = sys.stderr )
        print( "  Script 001 (build_feature_lookup) must run before this script.", file = sys.stderr )
        sys.exit( 1 )

    full_ids___features = load_feature_lookup( input_lookup_path )
    print( f"[002 {structure_name}] loaded {len( full_ids___features )} gene feature rows" )

    output_dir = Path( args.output_dir ) / structure_name / "2-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_summary_path = U.timestamped_output_path( output_dir, "2_ai-orthogroups-integrated_summary", output_base )

    header_columns = [
        "Structure_ID (phylogenetic species tree structure identifier)",
        "Orthogroup_ID (orthogroup identifier from OCL analysis)",
        "Origin_Phylogenetic_Block (phylogenetic block where the orthogroup originated format Parent_Clade_ID_Name::Child_Clade_ID_Name)",
        "Origin_Phylogenetic_Block_State (origin block in five-state vocabulary A O P L X with O marking Origin)",
        "Origin_Phylogenetic_Path (root-to-origin-child path of comma delimited clade_id_name values)",
        "Species_Count (total unique species in the orthogroup from OCL)",
        "Conservation_Events (count of phylogenetic blocks in state P from OCL)",
        "Loss_Events (count of phylogenetic blocks in state L from OCL)",
        "Continued_Absence_Events (count of phylogenetic blocks in state X from OCL)",
        "Orthogroup_Member_Count (number of member sequence identifiers in the orthogroup)",
        "Orthogroup_Sequence_IDs (comma delimited member GIGANTIC sequence identifiers)",
        "Dark_Integration_Count (number of member sequences classified dark in dark_proteome)",
        "Dark_Integration_Sequence_IDs (comma delimited member sequences classified dark)",
        "Dark_Members_Available_Count (number of members whose species had a dark_proteome classification)",
        "Hotspot_Integration_Count (number of member sequences that are members of a genomic hotspot)",
        "Hotspot_Integration_Sequence_IDs (comma delimited member sequences in a hotspot)",
        "Hotspot_Members_Available_Count (number of members whose species had a hotspots analysis)",
        "Secretome_Integration_Count (number of member sequences in the filtered secretome)",
        "Secretome_Integration_Sequence_IDs (comma delimited member sequences in the filtered secretome)",
        "Secretome_Members_Available_Count (number of members whose species had a filtered secretome)",
    ]

    orthogroup_count = 0
    with open( input_ocl_summary_path, 'r' ) as input_ocl_summary, \
         open( output_summary_path, 'w' ) as output_summary:
        output_summary.write( '\t'.join( header_columns ) + '\n' )

        # Orthogroup_ID (...)\tOrigin_Phylogenetic_Block (...)\t...\tSpecies_List (...)\tSequence_IDs (comma delimited list of GIGANTIC sequence identifiers in this orthogroup)
        # OG000000\tC000_OOL::C071_Basal\t...\tAbeoforma_whisleri,...\tg_10255c0g2-...,g_13896c2g2-...
        header_line = input_ocl_summary.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_origin_block = header_ids___indices[ "Origin_Phylogenetic_Block" ]
        index_origin_state = header_ids___indices[ "Origin_Phylogenetic_Block_State" ]
        index_origin_path = header_ids___indices[ "Origin_Phylogenetic_Path" ]
        index_species_count = header_ids___indices[ "Species_Count" ]
        index_conservation = header_ids___indices[ "Conservation_Events" ]
        index_loss = header_ids___indices[ "Loss_Events" ]
        index_continued_absence = header_ids___indices[ "Continued_Absence_Events" ]
        index_sequence_ids = header_ids___indices[ "Sequence_IDs" ]

        for line in input_ocl_summary:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ index_og ]
            sequence_ids_cell = parts[ index_sequence_ids ] if index_sequence_ids < len( parts ) else ""
            members = [ m for m in sequence_ids_cell.split( ',' ) if m ]

            dark_members = []
            hotspot_members = []
            secretome_members = []
            dark_available_count = 0
            hotspot_available_count = 0
            secretome_available_count = 0

            for member in members:
                features = full_ids___features.get( member )
                if features is None:
                    # Member absent from the feature lookup -> no source available.
                    continue
                is_dark, in_hotspot, is_secreted, dark_avail, hotspot_avail, secretome_avail = features
                if dark_avail == "True":
                    dark_available_count += 1
                    if is_dark == "True":
                        dark_members.append( member )
                if hotspot_avail == "True":
                    hotspot_available_count += 1
                    if in_hotspot == "True":
                        hotspot_members.append( member )
                if secretome_avail == "True":
                    secretome_available_count += 1
                    if is_secreted == "True":
                        secretome_members.append( member )

            output = '\t'.join( [
                structure_id,
                orthogroup_id,
                parts[ index_origin_block ],
                parts[ index_origin_state ],
                parts[ index_origin_path ],
                parts[ index_species_count ],
                parts[ index_conservation ],
                parts[ index_loss ],
                parts[ index_continued_absence ],
                str( len( members ) ),
                U.DELIM.join( members ),
                str( len( dark_members ) ),
                U.DELIM.join( dark_members ),
                str( dark_available_count ),
                str( len( hotspot_members ) ),
                U.DELIM.join( hotspot_members ),
                str( hotspot_available_count ),
                str( len( secretome_members ) ),
                U.DELIM.join( secretome_members ),
                str( secretome_available_count ),
            ] ) + '\n'
            output_summary.write( output )
            orthogroup_count += 1

    print( f"[002 {structure_name}] wrote {orthogroup_count} orthogroups -> {output_summary_path}" )


if __name__ == '__main__':
    main()
