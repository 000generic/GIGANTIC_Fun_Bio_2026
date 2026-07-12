#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Build the per-structure block-state expanded integration table (Table 2)
# Human: Eric Edsinger

"""
Script 003 — Block-state expanded integration table (Table 2), per structure.

Explodes each orthogroup across the phylogenetic blocks where it has a
meaningful state, repeating the orthogroup-level integration cells (from
Table 1) on each block-state row. This lets a user ask "at the node where this
orthogroup ORIGINATED / is CONSERVED / was LOST, which member genes integrate
with dark / hotspot / secretome?"

Inputs (both already produced for this structure):
  - Table 1 (2-output/2_ai-structure_NNN_orthogroups-integrated_summary.tsv)
      provides each orthogroup's integration cells (no re-aggregation needed).
  - OCL path_states (<ocl_orthogroups_dir>/structure_NNN/
      4_ai-path_states-per_orthogroup_per_species.tsv) provides, per orthogroup,
      the state letter on every phylogenetic block (via the per-species paths).

Block-state vocabulary (Rule 7): A O P L X. This table emits ONLY the states
where the orthogroup is present at the child or transitions there —
  O = Origin, P = Conservation (inherited presence), L = Loss.
Inherited-absence states A and X are intentionally excluded: the orthogroup is
absent there, so there are no member genes to integrate. (Documented design
decision — revisit if absence rows are wanted.)

One row per (structure, orthogroup, block, state). In-column lists use bare
commas (§34). Fail-fast: exits 1 on missing inputs or a block/state
inconsistency.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U

# Block-state letters that carry member genes at/through the child clade.
STATE_LETTERS___NAMES = {
    "O": "Origin",
    "P": "Conservation",
    "L": "Loss",
}

# Columns carried over from Table 1 (orthogroup-level integration COUNTS only).
# The large per-orthogroup sequence-ID list cells are intentionally NOT carried
# here: repeating them on every block-state row blew Table 2 up to ~20 GB per
# structure (~2 TB across 105). Counts are kept; the actual member / integration
# sequence IDs remain available once-per-orthogroup in Table 1 and per-gene in
# Table 3, joinable by Orthogroup_ID. (Design decision 2026-06-04, user-approved.)
CARRIED_COLUMNS = [
    "Orthogroup_Member_Count",
    "Dark_Integration_Count",
    "Dark_Members_Available_Count",
    "Hotspot_Integration_Count",
    "Hotspot_Members_Available_Count",
    "Secretome_Integration_Count",
    "Secretome_Members_Available_Count",
]


def load_table1( table1_path: Path ) -> dict:
    """orthogroup_id -> { carried_column : value } for the Table 1 integration cells."""
    orthogroups___cells = {}
    with open( table1_path, 'r' ) as input_table1:
        # Structure_ID (...)\tOrthogroup_ID (...)\t...\tOrthogroup_Sequence_IDs (...)\tDark_Integration_Count (...)\t...
        # 001\tOG000000\t...\tg_..,g_..\t5\t...
        header_line = input_table1.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        carried___indices = { col: header_ids___indices[ col ] for col in CARRIED_COLUMNS }
        for line in input_table1:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ index_og ]
            orthogroups___cells[ orthogroup_id ] = {
                col: ( parts[ idx ] if idx < len( parts ) else "" )
                for col, idx in carried___indices.items()
            }
    return orthogroups___cells


def build_orthogroup_block_states( path_states_path: Path ) -> dict:
    """
    orthogroup_id -> { phylogenetic_block : state_letter }.

    Reconstructed by walking each per-species path: a block is the consecutive
    pair ( clade[i], clade[i+1] ) and its state is path_state[i]. The state of a
    block for an orthogroup is invariant across the species paths that traverse
    it; an inconsistency indicates an upstream data problem and is fatal.
    """
    orthogroups___blocks___states = {}
    with open( path_states_path, 'r' ) as input_path_states:
        # Orthogroup_ID (...)\tSpecies_Clade_ID_Name (...)\tSpecies_In_Orthogroup (...)\tPhylogenetic_Path (comma delimited ...)\tPhylogenetic_Path_State (... letters A O P L X ...)
        # OG000000\tC001_Fonticula_alba\tFalse\tC000_OOL,C071_Basal,C072_Holomycota,C001_Fonticula_alba\tOPL
        header_line = input_path_states.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_path = header_ids___indices[ "Phylogenetic_Path" ]
        index_path_state = header_ids___indices[ "Phylogenetic_Path_State" ]

        for line in input_path_states:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ index_og ]
            clades = parts[ index_path ].split( ',' )
            path_state = parts[ index_path_state ] if index_path_state < len( parts ) else ""

            if len( path_state ) != len( clades ) - 1:
                print( f"CRITICAL ERROR: path/state length mismatch for {orthogroup_id}", file = sys.stderr )
                print( f"  path has {len( clades )} clades but state has {len( path_state )} letters.", file = sys.stderr )
                print( f"  line: {line[:200]}", file = sys.stderr )
                sys.exit( 1 )

            blocks___states = orthogroups___blocks___states.setdefault( orthogroup_id, {} )
            for i in range( len( clades ) - 1 ):
                phylogenetic_block = clades[ i ] + "::" + clades[ i + 1 ]
                state_letter = path_state[ i ]
                existing = blocks___states.get( phylogenetic_block )
                if existing is not None and existing != state_letter:
                    print( f"CRITICAL ERROR: inconsistent state for {orthogroup_id} block {phylogenetic_block}", file = sys.stderr )
                    print( f"  saw '{existing}' and '{state_letter}' across species paths.", file = sys.stderr )
                    sys.exit( 1 )
                blocks___states[ phylogenetic_block ] = state_letter
    return orthogroups___blocks___states


def main():
    parser = argparse.ArgumentParser( description = "Build block-state expanded table (Table 2)" )
    parser.add_argument( '--structure_id', required = True )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    structure_id = args.structure_id
    structure_name = f"structure_{structure_id}"

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    input_ocl_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "ocl_orthogroups_dir" ] )

    output_base = Path( args.output_dir )
    input_table1_path = U.resolve_timestamped_output_path(
        output_base / structure_name / "2-output", "2_ai-orthogroups-integrated_summary", output_base )
    input_path_states_path = input_ocl_dir / structure_name / "4_ai-path_states-per_orthogroup_per_species.tsv"

    if not input_table1_path.is_file():
        print( f"CRITICAL ERROR: Table 1 not found: {input_table1_path}", file = sys.stderr )
        print( "  Script 002 (build_integrated_summary) must run before this script.", file = sys.stderr )
        sys.exit( 1 )
    if not input_path_states_path.is_file():
        print( f"CRITICAL ERROR: OCL path_states not found: {input_path_states_path}", file = sys.stderr )
        print( "  This table needs the OCL path_states exposed in output_to_input.", file = sys.stderr )
        print( "  Ensure orthogroups_X_ocl exposes 4_ai-path_states-per_orthogroup_per_species.tsv", file = sys.stderr )
        print( "  per structure (see integrator AI_GUIDE — OCL path_states exposure).", file = sys.stderr )
        sys.exit( 1 )

    orthogroups___cells = load_table1( input_table1_path )
    orthogroups___blocks___states = build_orthogroup_block_states( input_path_states_path )
    print( f"[003 {structure_name}] table1 orthogroups: {len( orthogroups___cells )}; path_states orthogroups: {len( orthogroups___blocks___states )}" )

    output_dir = Path( args.output_dir ) / structure_name / "3-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_expanded_path = U.timestamped_output_path( output_dir, "3_ai-block_states-integrated_expanded", output_base )

    header_columns = [
        "Structure_ID (phylogenetic species tree structure identifier)",
        "Orthogroup_ID (orthogroup identifier from OCL analysis)",
        "Phylogenetic_Block (parent-to-child edge format Parent_Clade_ID_Name::Child_Clade_ID_Name)",
        "Block_State_Letter (Rule 7 state on this block; O Origin P Conservation L Loss)",
        "Block_State_Name (human readable block state; Origin Conservation or Loss)",
        "Parent_Clade_ID_Name (parent endpoint clade_id_name of the block)",
        "Child_Clade_ID_Name (child endpoint clade_id_name of the block)",
        "Orthogroup_Member_Count (number of member sequence identifiers in the orthogroup)",
        "Dark_Integration_Count (number of member sequences classified dark in dark_proteome; join Orthogroup_ID to Table 1 for the IDs)",
        "Dark_Members_Available_Count (number of members whose species had a dark_proteome classification)",
        "Hotspot_Integration_Count (number of member sequences that are members of a genomic hotspot; join Orthogroup_ID to Table 1 for the IDs)",
        "Hotspot_Members_Available_Count (number of members whose species had a hotspots analysis)",
        "Secretome_Integration_Count (number of member sequences in the filtered secretome; join Orthogroup_ID to Table 1 for the IDs)",
        "Secretome_Members_Available_Count (number of members whose species had a filtered secretome)",
    ]

    row_count = 0
    with open( output_expanded_path, 'w' ) as output_expanded:
        output_expanded.write( '\t'.join( header_columns ) + '\n' )
        for orthogroup_id in sorted( orthogroups___blocks___states.keys() ):
            cells = orthogroups___cells.get( orthogroup_id )
            if cells is None:
                # Orthogroup present in path_states but not in Table 1 — should
                # not happen (same OCL run). Surface, do not silently skip.
                print( f"CRITICAL ERROR: orthogroup {orthogroup_id} in path_states but absent from Table 1", file = sys.stderr )
                sys.exit( 1 )
            blocks___states = orthogroups___blocks___states[ orthogroup_id ]
            for phylogenetic_block in sorted( blocks___states.keys() ):
                state_letter = blocks___states[ phylogenetic_block ]
                if state_letter not in STATE_LETTERS___NAMES:
                    continue  # skip inherited-absence states A and X (no member genes)
                parent_clade, child_clade = phylogenetic_block.split( "::", 1 )
                output = '\t'.join( [
                    structure_id,
                    orthogroup_id,
                    phylogenetic_block,
                    state_letter,
                    STATE_LETTERS___NAMES[ state_letter ],
                    parent_clade,
                    child_clade,
                ] + [ cells[ col ] for col in CARRIED_COLUMNS ] ) + '\n'
                output_expanded.write( output )
                row_count += 1

    print( f"[003 {structure_name}] wrote {row_count} block-state rows -> {output_expanded_path}" )


if __name__ == '__main__':
    main()
