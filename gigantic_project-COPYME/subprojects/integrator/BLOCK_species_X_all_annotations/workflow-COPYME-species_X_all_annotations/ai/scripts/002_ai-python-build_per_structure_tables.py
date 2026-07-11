#!/usr/bin/env python3
# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Phase 2 — for one species-tree structure, append orthogroup + annogroup OCL columns onto each per-species base table (full wide table per structure)
# Human: Eric Edsinger

"""
Script 002 — Phase 2: per-structure full wide proteome tables.

Runs ONCE per species-tree structure (NextFlow fans this out over the resolved
`structures` list). It reads the structure-invariant base tables from Phase 1
(1-output/_shared/) and appends this structure's OCL (Origin-Conservation-Loss)
columns, producing the full wide table the user asked for:
  2-output/<structure>/<phyloname>-proteome_all_annotations.tsv

OCL inference is structure-DEPENDENT, so each structure gets its own complete
set of per-species tables (all base columns + this structure's OCL columns).

Two OCL sources (per structure):
  - orthogroups OCL : <run>/<structure>/4_ai-orthogroups-complete_ocl_summary.tsv
        joined via each protein's Orthogroup_ID (from the base table).
  - annogroup OCL   : <run>/<structure>/4_ai-structure_<NNN>_annogroups-complete_ocl_summary-all_types.tsv
        joined via each protein's pfam annogroup IDs (parallel lists, all types).

Research-integrity (per AI_BEHAVIOR.md):
  - Every non-NA Orthogroup_ID MUST resolve in the orthogroup OCL summary
    (membership is structure-invariant; every orthogroup appears in every
    structure's OCL). A non-resolving orthogroup means the orthogroups table
    and the OCL run are out of sync -> fail-fast (exit 1), never a silent NA.
  - annogroup OCL coverage can legitimately LAG annogroup membership (the pfam
    OCL run is a snapshot; go/panther OCL is not run at all). An annogroup ID
    with no OCL row is recorded NA in its parallel slot AND counted; the count
    is printed so the skew is visible, never hidden.

Fail-fast: exits 1 if the structure's OCL summaries or the base tables are missing.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_species_X_all_annotations as U


# OCL columns appended to the base table (self-documenting headers, §34).
OCL_HEADER_COLUMNS = [
    "Structure_ID (species-tree structure whose OCL inference populates the OCL columns in this table)",
    "Orthogroup_OCL_Origin_Phylogenetic_Block (origin parent::child phylogenetic block for this protein's orthogroup on this structure; NA if no orthogroup)",
    "Orthogroup_OCL_Origin_Phylogenetic_Block_State (origin block in the five-state vocabulary A O P L X; NA if no orthogroup)",
    "Orthogroup_OCL_Origin_Phylogenetic_Path (comma delimited root to origin-child clade path for the orthogroup; NA if no orthogroup or absent in source)",
    "Orthogroup_OCL_Conservation_Events (count of inherited-presence P blocks for the orthogroup on this structure; NA if no orthogroup)",
    "Orthogroup_OCL_Loss_Events (count of loss L blocks for the orthogroup on this structure; NA if no orthogroup)",
    "Orthogroup_OCL_Continued_Absence_Events (count of inherited-absence X blocks for the orthogroup on this structure; NA if no orthogroup)",
    "Annogroup_Pfam_OCL_IDs (comma delimited pfam annogroup identifiers this protein belongs to; parallel to the Annogroup_Pfam_OCL_* columns; NA if none)",
    "Annogroup_Pfam_OCL_Origin_Phylogenetic_Blocks (comma delimited origin blocks parallel to Annogroup_Pfam_OCL_IDs; NA token per annogroup with no OCL row)",
    "Annogroup_Pfam_OCL_Origin_Phylogenetic_Paths (semicolon delimited origin paths parallel to Annogroup_Pfam_OCL_IDs since each path is itself comma delimited; NA token per annogroup with no OCL row)",
    "Annogroup_Pfam_OCL_Conservation_Events (comma delimited conservation event counts parallel to Annogroup_Pfam_OCL_IDs; NA token per annogroup with no OCL row)",
    "Annogroup_Pfam_OCL_Loss_Events (comma delimited loss event counts parallel to Annogroup_Pfam_OCL_IDs; NA token per annogroup with no OCL row)",
    "Annogroup_Pfam_OCL_Continued_Absence_Events (comma delimited continued absence event counts parallel to Annogroup_Pfam_OCL_IDs; NA token per annogroup with no OCL row)",
]


def load_orthogroup_ocl( summary_path: Path ) -> dict:
    """orthogroup id -> ( origin_block, origin_block_state, origin_path, conservation, loss, continued_absence )."""
    orthogroups___ocl = {}
    with open( summary_path, 'r' ) as input_summary:
        header_ids___indices = U.build_header_index( input_summary.readline() )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_block = header_ids___indices[ "Origin_Phylogenetic_Block" ]
        index_state = header_ids___indices[ "Origin_Phylogenetic_Block_State" ]
        index_path = header_ids___indices[ "Origin_Phylogenetic_Path" ]
        index_conservation = header_ids___indices[ "Conservation_Events" ]
        index_loss = header_ids___indices[ "Loss_Events" ]
        index_continued = header_ids___indices[ "Continued_Absence_Events" ]
        for line in input_summary:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroups___ocl[ parts[ index_og ] ] = (
                parts[ index_block ], parts[ index_state ], parts[ index_path ],
                parts[ index_conservation ], parts[ index_loss ], parts[ index_continued ],
            )
    return orthogroups___ocl


def load_annogroup_ocl( summary_path: Path ) -> dict:
    """annogroup id -> ( origin_block, origin_path, conservation, loss, continued_absence )."""
    annogroups___ocl = {}
    with open( summary_path, 'r' ) as input_summary:
        header_ids___indices = U.build_header_index( input_summary.readline() )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_block = header_ids___indices[ "Origin_Phylogenetic_Block" ]
        index_path = header_ids___indices[ "Origin_Phylogenetic_Path" ]
        index_conservation = header_ids___indices[ "Conservation_Events" ]
        index_loss = header_ids___indices[ "Loss_Events" ]
        index_continued = header_ids___indices[ "Continued_Absence_Events" ]
        for line in input_summary:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroups___ocl[ parts[ index_annogroup ] ] = (
                parts[ index_block ], parts[ index_path ],
                parts[ index_conservation ], parts[ index_loss ], parts[ index_continued ],
            )
    return annogroups___ocl


def main():
    parser = argparse.ArgumentParser( description = "Phase 2 — per-structure full wide proteome tables" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    parser.add_argument( '--structure', required = True, help = "structure_NNN to materialize" )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    structure = args.structure
    structure_number = structure.replace( "structure_", "" )

    orthogroups_ocl_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "orthogroups_ocl_dir" ] )
    annogroup_ocl_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "annogroup_ocl_dir" ] )
    orthogroups_ocl_run_label = config[ "orthogroups_ocl_run_label" ]
    annogroup_ocl_run_label = config[ "annogroup_ocl_run_label" ]

    orthogroups_summary_path = orthogroups_ocl_dir / orthogroups_ocl_run_label / structure / "4_ai-orthogroups-complete_ocl_summary.tsv"
    annogroup_summary_path = annogroup_ocl_dir / annogroup_ocl_run_label / structure / f"4_ai-structure_{structure_number}_annogroups-complete_ocl_summary-all_types.tsv"

    for required in ( orthogroups_summary_path, annogroup_summary_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: OCL summary not found for {structure}: {required}", file = sys.stderr )
            sys.exit( 1 )

    shared_dir = Path( args.output_dir ) / "1-output" / "_shared"
    base_files = sorted( shared_dir.glob( "*-proteome_annotations-base*.tsv" ) )
    if not base_files:
        print( f"CRITICAL ERROR: no base tables in {shared_dir} — Script 001 must run first", file = sys.stderr )
        sys.exit( 1 )

    timestamp_suffix = U.resolve_run_timestamp_suffix( shared_dir )
    print( f"[002] {structure}: using run timestamp suffix {timestamp_suffix}" )

    print( f"[002] {structure}: loading orthogroup OCL summary" )
    orthogroups___ocl = load_orthogroup_ocl( orthogroups_summary_path )
    print( f"[002] {structure}: {len( orthogroups___ocl )} orthogroups in OCL summary" )
    print( f"[002] {structure}: loading annogroup OCL summary (pfam, all types)" )
    annogroups___ocl = load_annogroup_ocl( annogroup_summary_path )
    print( f"[002] {structure}: {len( annogroups___ocl )} annogroups in OCL summary" )

    output_structure_dir = Path( args.output_dir ) / "2-output" / structure
    output_structure_dir.mkdir( parents = True, exist_ok = True )

    orthogroup_unresolved = 0
    annogroup_id_total = 0
    annogroup_id_unresolved = 0

    for base_file in base_files:
        phyloname = base_file.name.split( "-proteome_annotations-base" )[ 0 ]
        output_table_path = output_structure_dir / (
            f"{phyloname}-proteome_all_annotations{timestamp_suffix}.tsv"
        )
        with open( base_file, 'r' ) as input_base, open( output_table_path, 'w' ) as output_table:
            base_header_line = input_base.readline().rstrip( '\n' )
            header_ids___indices = U.build_header_index( base_header_line )
            index_orthogroup = header_ids___indices[ "Orthogroup_ID" ]
            index_annogroup_pfam = header_ids___indices[ "Annogroups_Pfam_Identifiers" ]

            output_table.write( base_header_line + '\t' + '\t'.join( OCL_HEADER_COLUMNS ) + '\n' )

            for line in input_base:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )

                # ---- orthogroup OCL ------------------------------------
                orthogroup_id = parts[ index_orthogroup ]
                if orthogroup_id == U.NA:
                    og_block = og_state = og_path = og_conservation = og_loss = og_continued = U.NA
                else:
                    ocl = orthogroups___ocl.get( orthogroup_id )
                    if ocl is None:
                        # structure-invariant membership vs OCL run out of sync.
                        orthogroup_unresolved += 1
                        print(
                            f"CRITICAL ERROR: {structure}: orthogroup {orthogroup_id} (protein in base table) "
                            f"has no row in the orthogroup OCL summary {orthogroups_summary_path}. "
                            "The orthogroups membership and the OCL run are out of sync.",
                            file = sys.stderr,
                        )
                        sys.exit( 1 )
                    ( og_block, og_state, og_path, og_conservation, og_loss, og_continued ) = ocl

                # ---- annogroup pfam OCL (parallel lists, all types) ----
                annogroup_cell = parts[ index_annogroup_pfam ]
                if annogroup_cell == U.NA:
                    annogroup_ids_out = U.NA
                    annogroup_blocks_out = U.NA
                    annogroup_paths_out = U.NA
                    annogroup_conservation_out = U.NA
                    annogroup_loss_out = U.NA
                    annogroup_continued_out = U.NA
                else:
                    annogroup_ids = [ token for token in annogroup_cell.split( U.DELIM ) if token ]
                    ids_list = []
                    blocks_list = []
                    paths_list = []
                    conservation_list = []
                    loss_list = []
                    continued_list = []
                    for annogroup_id in annogroup_ids:
                        annogroup_id_total += 1
                        ocl = annogroups___ocl.get( annogroup_id )
                        ids_list.append( annogroup_id )
                        if ocl is None:
                            annogroup_id_unresolved += 1
                            blocks_list.append( U.NA )
                            paths_list.append( U.NA )
                            conservation_list.append( U.NA )
                            loss_list.append( U.NA )
                            continued_list.append( U.NA )
                        else:
                            ( ag_block, ag_path, ag_conservation, ag_loss, ag_continued ) = ocl
                            blocks_list.append( ag_block )
                            paths_list.append( ag_path )
                            conservation_list.append( ag_conservation )
                            loss_list.append( ag_loss )
                            continued_list.append( ag_continued )
                    annogroup_ids_out = U.DELIM.join( ids_list )
                    annogroup_blocks_out = U.DELIM.join( blocks_list )
                    annogroup_paths_out = U.SUBDELIM.join( paths_list )
                    annogroup_conservation_out = U.DELIM.join( conservation_list )
                    annogroup_loss_out = U.DELIM.join( loss_list )
                    annogroup_continued_out = U.DELIM.join( continued_list )

                ocl_fields = [
                    structure,
                    og_block, og_state, og_path, og_conservation, og_loss, og_continued,
                    annogroup_ids_out, annogroup_blocks_out, annogroup_paths_out,
                    annogroup_conservation_out, annogroup_loss_out, annogroup_continued_out,
                ]
                output_table.write( line + '\t' + '\t'.join( ocl_fields ) + '\n' )

        print( f"[002] {structure}: wrote {output_table_path.name}" )

    if annogroup_id_total > 0 and annogroup_id_unresolved > 0:
        fraction = 100.0 * annogroup_id_unresolved / annogroup_id_total
        print(
            f"[002] {structure}: NOTE — {annogroup_id_unresolved} of {annogroup_id_total} "
            f"pfam annogroup references ({fraction:.1f}%) had no OCL row (annogroup OCL coverage "
            f"lags membership). Recorded NA in their OCL slots (visible, not hidden)."
        )

    print( f"[002] {structure}: done ({len( base_files )} species tables) -> {output_structure_dir}" )


if __name__ == '__main__':
    main()
