#!/usr/bin/env python3
# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Validate the species_X_all_annotations base + per-structure tables (strict fail-fast, §36)
# Human: Eric Edsinger

"""
Script 003 — Validation (strict fail-fast per gigantic_conventions §36).

Cross-checks the per-species base tables and the per-structure wide tables for
internal consistency and join integrity. ANY failure writes a FAIL report and
exits 1 (a silent join artifact in a published per-protein table is a research
integrity failure, per AI_BEHAVIOR.md).

Base-table checks (1-output/_shared/):
  B1. >= 1 base table present; each has the full required header; each non-empty.
  B2. Sequence_Identifier unique within each species file.
  B3. Every row's Sequence_Identifier resolves to the file's own phyloname — no
      cross-species join contamination.
  B4. Availability-flag consistency: when a source flag is 'no', the columns fed
      by that source are NA on every row (a non-NA value would be a leak).
  B5. Per annotation type: Species_Count in {0,1}; Sequence_Count in [0, #identifiers];
      identifiers sorted and unique; coverage consistency (0 counts iff empty ids).

Per-structure checks (2-output/<structure>/):
  S1. Each structure dir has exactly one wide table per base table; each wide
      table's row count equals its base table's row count.
  S2. Each wide table has the OCL header columns; Structure_ID equals the dir.
  S3. Referential integrity: every non-NA Orthogroup_ID has a non-NA
      Orthogroup_OCL_Origin_Phylogenetic_Block (a non-NA OG with NA OCL would be
      a silent join miss).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_species_X_all_annotations as U

ANNOTATION_TYPE_PREFIXES = [
    "Pfam", "InterPro_GO", "PANTHER_GO", "PANTHER",
    "Annogroups_Pfam", "Annogroups_GO", "Annogroups_PANTHER",
    "Gene_Groups", "Gene_Families",
]
NAMES_BLANK_PREFIXES = { "Gene_Groups", "Gene_Families" }

REQUIRED_BASE_HEADER_IDS = [
    "Sequence_Identifier", "Phyloname", "Genus_Species", "Sequence_Length", "Protein_Sequence",
    "Gene_Size_BP", "CDS_Size_BP", "Protein_Size_AA", "Gene_Sizes_Available",
    "In_Hotspot", "Hotspot_IDs", "Hotspot_Paralog_Counts", "Hotspots_Available",
    "Top_3_NR_Hits",
] + [
    column.split( ' (' )[ 0 ]
    for prefix in ANNOTATION_TYPE_PREFIXES
    for column in U.feature_header_columns( prefix, "placeholder" )
] + [
    "Annotations_HMMs_Available",
    "Orthogroup_ID", "Orthogroup_Member_Protein_Count", "Orthogroup_Species_Count",
    "Secretome_SignalP_Call", "Secretome_SignalP_Probability", "Secretome_DeepLoc_Localization",
    "Secretome_Available",
    "Dark_Status", "Dark_Proteome_Available",
]

REQUIRED_OCL_HEADER_IDS = [
    "Structure_ID",
    "Orthogroup_OCL_Origin_Phylogenetic_Block", "Orthogroup_OCL_Origin_Phylogenetic_Block_State",
    "Orthogroup_OCL_Origin_Phylogenetic_Path", "Orthogroup_OCL_Conservation_Events",
    "Orthogroup_OCL_Loss_Events", "Orthogroup_OCL_Continued_Absence_Events",
    "Annogroup_Pfam_OCL_IDs", "Annogroup_Pfam_OCL_Origin_Phylogenetic_Blocks",
    "Annogroup_Pfam_OCL_Origin_Phylogenetic_Paths", "Annogroup_Pfam_OCL_Conservation_Events",
    "Annogroup_Pfam_OCL_Loss_Events", "Annogroup_Pfam_OCL_Continued_Absence_Events",
]

# ( availability flag header, [ columns that must be NA when flag == 'no' ] )
AVAILABILITY_CONSISTENCY = [
    ( "Gene_Sizes_Available", [ "Gene_Size_BP", "CDS_Size_BP", "Protein_Size_AA" ] ),
    ( "Hotspots_Available", [ "In_Hotspot", "Hotspot_IDs", "Hotspot_Paralog_Counts" ] ),
    ( "Annotations_HMMs_Available", [
        "Pfam_Species_Count", "Pfam_Sequence_Count", "Pfam_Identifiers", "Pfam_Names",
        "InterPro_GO_Species_Count", "InterPro_GO_Sequence_Count", "InterPro_GO_Identifiers", "InterPro_GO_Names",
        "PANTHER_GO_Species_Count", "PANTHER_GO_Sequence_Count", "PANTHER_GO_Identifiers", "PANTHER_GO_Names",
        "PANTHER_Species_Count", "PANTHER_Sequence_Count", "PANTHER_Identifiers", "PANTHER_Names",
    ] ),
    ( "Secretome_Available", [ "Secretome_SignalP_Call", "Secretome_SignalP_Probability", "Secretome_DeepLoc_Localization" ] ),
    ( "Dark_Proteome_Available", [ "Dark_Status" ] ),
]


def phyloname_from_base_filename( filename: str ) -> str:
    return filename.split( "-proteome_annotations-base" )[ 0 ]


def validate_annotation_columns( failures: list, file_label: str, parts: list, header_ids___indices: dict ):
    for prefix in ANNOTATION_TYPE_PREFIXES:
        index_species = header_ids___indices[ f"{prefix}_Species_Count" ]
        index_sequence = header_ids___indices[ f"{prefix}_Sequence_Count" ]
        index_identifiers = header_ids___indices[ f"{prefix}_Identifiers" ]
        index_names = header_ids___indices[ f"{prefix}_Names" ]

        species_count_text = parts[ index_species ]
        sequence_count_text = parts[ index_sequence ]
        identifiers_cell = parts[ index_identifiers ]
        names_cell = parts[ index_names ]

        if species_count_text == U.NA:
            continue

        try:
            species_count = int( species_count_text )
            sequence_count = int( sequence_count_text )
        except ValueError:
            failures.append( f"B5: {file_label} {prefix} counts are not integers" )
            continue

        identifiers = [ token for token in identifiers_cell.split( U.DELIM ) if token ] if identifiers_cell else []
        names = names_cell.split( U.NAME_DELIM ) if names_cell else []

        if species_count not in ( 0, 1 ):
            failures.append( f"B5: {file_label} {prefix}_Species_Count {species_count} not in {{0,1}}" )
        if sequence_count < 0 or sequence_count != len( identifiers ):
            failures.append(
                f"B5: {file_label} {prefix}_Sequence_Count {sequence_count} != #identifiers {len( identifiers )}"
            )
        if identifiers != sorted( identifiers ):
            failures.append( f"B5: {file_label} {prefix}_Identifiers not sorted" )
        if len( identifiers ) != len( set( identifiers ) ):
            failures.append( f"B5: {file_label} {prefix}_Identifiers contain duplicates" )
        if ( sequence_count == 0 ) != ( len( identifiers ) == 0 ):
            failures.append( f"B5: {file_label} {prefix} coverage inconsistency" )
        if prefix in NAMES_BLANK_PREFIXES:
            if names_cell.strip():
                failures.append( f"B5: {file_label} {prefix}_Names must be blank but is {names_cell!r}" )
        elif len( identifiers ) != len( names ):
            failures.append(
                f"B5: {file_label} {prefix} identifier/name count mismatch "
                f"({len( identifiers )} vs {len( names )})"
            )


def main():
    parser = argparse.ArgumentParser( description = "Validate species_X_all_annotations results (fail-fast)" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    output_base = Path( args.output_dir )
    shared_dir = output_base / "1-output" / "_shared"
    structures_root = output_base / "2-output"
    timestamp_suffix = U.resolve_run_timestamp_suffix( shared_dir )

    failures = []

    base_files = sorted( shared_dir.glob( "*-proteome_annotations-base*.tsv" ) )
    if not base_files:
        print( f"CRITICAL ERROR: no base tables found in {shared_dir}", file = sys.stderr )
        sys.exit( 1 )

    phylonames___row_counts = {}
    total_proteins = 0

    # ---- BASE checks ------------------------------------------------------
    for base_file in base_files:
        phyloname = phyloname_from_base_filename( base_file.name )
        with open( base_file, 'r' ) as input_base:
            header_ids___indices = U.build_header_index( input_base.readline() )

            missing_headers = [ header_id for header_id in REQUIRED_BASE_HEADER_IDS if header_id not in header_ids___indices ]
            if missing_headers:
                failures.append( f"B1: {base_file.name} missing header(s): {missing_headers}" )
                phylonames___row_counts[ phyloname ] = 0
                continue

            index_sequence = header_ids___indices[ "Sequence_Identifier" ]
            consistency_indices = [
                ( header_ids___indices[ flag_id ], [ header_ids___indices[ col ] for col in cols ] )
                for ( flag_id, cols ) in AVAILABILITY_CONSISTENCY
            ]

            seen_sequences = set()
            row_count = 0
            for line in input_base:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                row_count += 1
                sequence_identifier = parts[ index_sequence ]

                # B2 uniqueness
                if sequence_identifier in seen_sequences:
                    failures.append( f"B2: {base_file.name} duplicate Sequence_Identifier {sequence_identifier}" )
                else:
                    seen_sequences.add( sequence_identifier )

                # B3 species containment
                ( _gene, row_phyloname, _genus ) = U.parse_full_gigantic_id( sequence_identifier )
                if row_phyloname != phyloname:
                    failures.append(
                        f"B3: {base_file.name} row Sequence_Identifier resolves to phyloname "
                        f"'{row_phyloname}' but file is '{phyloname}'"
                    )

                # B4 availability-flag consistency
                for ( flag_index, column_indices ) in consistency_indices:
                    if parts[ flag_index ] == "no":
                        for column_index in column_indices:
                            if parts[ column_index ] != U.NA:
                                failures.append(
                                    f"B4: {base_file.name} availability flag 'no' but column index "
                                    f"{column_index} is '{parts[ column_index ]}' (expected NA)"
                                )
                                break

                validate_annotation_columns( failures, base_file.name, parts, header_ids___indices )

            phylonames___row_counts[ phyloname ] = row_count
            total_proteins += row_count
            if row_count == 0:
                failures.append( f"B1: {base_file.name} has zero data rows" )

    # ---- PER-STRUCTURE checks --------------------------------------------
    structure_dirs = sorted( path for path in structures_root.glob( "structure_*" ) if path.is_dir() ) if structures_root.is_dir() else []
    structures_validated = []
    for structure_dir in structure_dirs:
        structure = structure_dir.name
        structures_validated.append( structure )
        wide_files = sorted( structure_dir.glob( "*-proteome_all_annotations*.tsv" ) )

        if len( wide_files ) != len( base_files ):
            failures.append( f"S1: {structure} has {len( wide_files )} wide tables but {len( base_files )} base tables exist" )

        for wide_file in wide_files:
            phyloname = wide_file.name.split( "-proteome_all_annotations" )[ 0 ]
            expected_rows = phylonames___row_counts.get( phyloname )
            with open( wide_file, 'r' ) as input_wide:
                header_ids___indices = U.build_header_index( input_wide.readline() )
                missing_ocl = [ header_id for header_id in REQUIRED_OCL_HEADER_IDS if header_id not in header_ids___indices ]
                if missing_ocl:
                    failures.append( f"S2: {structure}/{wide_file.name} missing OCL header(s): {missing_ocl}" )
                    continue
                index_structure = header_ids___indices[ "Structure_ID" ]
                index_orthogroup = header_ids___indices[ "Orthogroup_ID" ]
                index_og_block = header_ids___indices[ "Orthogroup_OCL_Origin_Phylogenetic_Block" ]

                row_count = 0
                for line in input_wide:
                    line = line.rstrip( '\n' )
                    if not line:
                        continue
                    parts = line.split( '\t' )
                    row_count += 1
                    if parts[ index_structure ] != structure:
                        failures.append( f"S2: {structure}/{wide_file.name} Structure_ID '{parts[ index_structure ]}' != '{structure}'" )
                    # S3 referential integrity
                    if parts[ index_orthogroup ] != U.NA and parts[ index_og_block ] == U.NA:
                        failures.append(
                            f"S3: {structure}/{wide_file.name} orthogroup {parts[ index_orthogroup ]} has NA OCL origin block (join miss)"
                        )

                if expected_rows is not None and row_count != expected_rows:
                    failures.append(
                        f"S1: {structure}/{wide_file.name} row count {row_count} != base row count {expected_rows}"
                    )

    # ---- report -----------------------------------------------------------
    output_dir = output_base / "3-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    report_filename = U.build_timestamped_validation_report_filename( timestamp_suffix )
    output_report_path = output_dir / report_filename

    status = "PASS" if not failures else "FAIL"
    report_lines = [
        "=" * 78,
        "GIGANTIC integrator - species_X_all_annotations - VALIDATION REPORT",
        "=" * 78,
        "",
        f"Status: {status}",
        f"Run timestamp suffix: {timestamp_suffix}",
        "",
        f"Species base tables:        {len( base_files )}",
        f"Total proteins (all base):  {total_proteins}",
        f"Structures materialized:    {len( structures_validated )} ({', '.join( structures_validated ) if structures_validated else 'none'})",
        "",
        f"Failures: {len( failures )}",
    ]
    for failure in failures[ :200 ]:
        report_lines.append( f"  - {failure}" )
    if len( failures ) > 200:
        report_lines.append( f"  ... and {len( failures ) - 200} more" )
    report_lines.extend( [ "", "=" * 78 ] )

    with open( output_report_path, 'w' ) as output_report:
        output_report.write( '\n'.join( report_lines ) + '\n' )

    pointer_path = output_dir / "3_ai-validation_report_filename.txt"
    pointer_path.write_text( report_filename + '\n' )

    print( f"[003] validation {status} -> {output_report_path}" )

    if failures:
        print( f"CRITICAL ERROR: validation FAILED with {len( failures )} issue(s). See {output_report_path}", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
