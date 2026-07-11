#!/usr/bin/env python3
# AI: Claude (Cursor) | Opus 4.8 | 2026 July 10 | Purpose: Fail-fast validation of the orthogroups_X_all_annotations table (§36)
# Human: Eric Edsinger

"""
Script 002 — Validate the orthogroups_X_all_annotations table (fail-fast, §36).

Independent cross-checks that rely only on the Script 001 output table plus the
orthogroups input row count (so a bug in 001 cannot hide behind shared code):

  Global
    - output table exists and has a header + >=1 data row
    - data row count == orthogroup count in the input orthogroups file
    - Orthogroup_ID values are non-empty and unique

  Per row
    - Member_Sequence_Count is a positive integer == number of Sequence_IDs
    - Is_Singleton == (yes iff Member_Sequence_Count == 1)
    - deconvolution completeness: sum of the species (tip) columns == Member_Sequence_Count
    - every full-coverage clade column == Member_Sequence_Count
    - every clade column value is between 0 and Member_Sequence_Count (inclusive)

  Per annotation type (Pfam, GO, PANTHER, Annogroups_Pfam, Annogroups_GO,
                       Annogroups_PANTHER, Gene_Families, Gene_Groups,
                       Dark_Proteome, Hotspots)
    - identifiers unique and sorted
    - #identifiers == #names, unless the type has blank names (Hotspots), in
      which case the names cell must be empty

Writes a PASS/FAIL report to 2-output/ and exits 1 on any failure.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_orthogroups_X_all_annotations as U


# Annotation type prefixes with blank-name flag, in output column order. The HMM
# display prefixes come from config; the remaining four are fixed for this block.
NAMES_BLANK_PREFIXES = { "Hotspots" }
HMM_DISPLAY = { "pfam": "Pfam", "go": "GO", "panther": "PANTHER" }
EXTRA_PREFIXES = [ "Gene_Families", "Gene_Groups", "Dark_Proteome", "Hotspots" ]
ANNOGROUP_PREFIXES = [ "Annogroups_Pfam", "Annogroups_GO", "Annogroups_PANTHER" ]


def count_input_orthogroups( orthogroups_path: Path ) -> int:
    count = 0
    with open( orthogroups_path, 'r' ) as input_orthogroups:
        for line in input_orthogroups:
            if line.strip():
                count += 1
    return count


def descendant_species_count_from_header( header_text: str ):
    """Parse 'K descendant species' out of a clade column header; None for tips."""
    marker = " descendant species"
    if marker not in header_text:
        return None
    before = header_text.split( marker )[ 0 ]
    token = before.rsplit( ' ', 1 )[ -1 ]
    return int( token ) if token.isdigit() else None


def main():
    parser = argparse.ArgumentParser( description = "Validate the orthogroups_X_all_annotations table" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    hmm_sources = config[ "hmm_annotation_sources" ]
    annogroup_sources = config.get( "annogroup_sources", [ "pfam", "go", "panther" ] )
    orthogroups_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "orthogroups_file" ] )

    type_prefixes = (
        [ HMM_DISPLAY.get( source, source.capitalize() ) for source in hmm_sources ]
        + [ U.annogroup_prefix_for_source( source ) for source in annogroup_sources ]
        + EXTRA_PREFIXES
    )

    output_base = Path( args.output_dir )
    table_path = U.resolve_output_table_path( output_base )
    report_dir = output_base / "2-output"
    report_dir.mkdir( parents = True, exist_ok = True )
    report_path = report_dir / "2_ai-validation_report.txt"

    failures = []
    checks = []

    def check( ok: bool, description: str, detail: str = "" ):
        checks.append( ( ok, description, detail ) )
        if not ok:
            failures.append( f"{description}: {detail}" )

    if not table_path.is_file():
        report_path.write_text( f"FAIL\nMissing output table: {table_path}\n" )
        print( f"CRITICAL ERROR: output table not found: {table_path}", file = sys.stderr )
        sys.exit( 1 )

    with open( table_path, 'r' ) as input_table:
        header_line = input_table.readline().rstrip( '\n' )
        header_columns = header_line.split( '\t' )
        header_ids___indices = U.build_header_index( header_line )

        index_orthogroup = header_ids___indices[ "Orthogroup_ID" ]
        index_sequences = header_ids___indices[ "Sequence_IDs" ]
        index_count = header_ids___indices[ "Member_Sequence_Count" ]
        index_singleton = header_ids___indices[ "Is_Singleton" ]

        # { prefix: ( identifiers_index, names_index ) }
        type_indices = {}
        for prefix in type_prefixes:
            type_indices[ prefix ] = (
                header_ids___indices[ f"{prefix}_Identifiers" ],
                header_ids___indices[ f"{prefix}_Names" ],
            )

        fixed_and_annotation = { index_orthogroup, index_sequences, index_count, index_singleton }
        for indices in type_indices.values():
            fixed_and_annotation.update( indices )

        tip_column_indices = []
        clade_column_indices = []
        for index, column in enumerate( header_columns ):
            if index in fixed_and_annotation:
                continue
            clade_column_indices.append( index )
            if "within tip" in column:
                tip_column_indices.append( index )
        number_of_tips = len( tip_column_indices )
        full_coverage_indices = [
            index for index in clade_column_indices
            if descendant_species_count_from_header( header_columns[ index ] ) == number_of_tips
        ]

        check( number_of_tips > 0, "Tip (species) columns present", f"found {number_of_tips}" )
        check( len( full_coverage_indices ) > 0, "At least one full-coverage (root) clade column",
               f"found {len( full_coverage_indices )}" )
        check( len( type_indices ) == len( type_prefixes ), "All ten annotation types present",
               f"found {len( type_indices )} of {len( type_prefixes )}" )

        seen_orthogroups = set()
        duplicate_orthogroups = 0
        data_rows = 0
        for line in input_table:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            data_rows += 1

            og_id = parts[ index_orthogroup ]
            if not og_id:
                failures.append( f"row {data_rows}: empty Orthogroup_ID" )
            if og_id in seen_orthogroups:
                duplicate_orthogroups += 1
            seen_orthogroups.add( og_id )

            member_count = int( parts[ index_count ] ) if parts[ index_count ].isdigit() else -1
            sequence_ids = [ token for token in parts[ index_sequences ].split( U.DELIM ) if token ]
            if member_count != len( sequence_ids ):
                failures.append( f"{og_id}: Member_Sequence_Count {member_count} != #Sequence_IDs {len( sequence_ids )}" )
            expected_singleton = "yes" if member_count == 1 else "no"
            if parts[ index_singleton ] != expected_singleton:
                failures.append( f"{og_id}: Is_Singleton {parts[ index_singleton ]!r} != expected {expected_singleton!r}" )

            tip_sum = sum( int( parts[ index ] ) for index in tip_column_indices )
            if tip_sum != member_count:
                failures.append( f"{og_id}: sum of species (tip) columns {tip_sum} != Member_Sequence_Count {member_count}" )
            for index in full_coverage_indices:
                if int( parts[ index ] ) != member_count:
                    failures.append( f"{og_id}: full-coverage clade column '{header_columns[ index ].split(' (')[0]}' "
                                     f"= {parts[ index ]} != Member_Sequence_Count {member_count}" )
            for index in clade_column_indices:
                value = int( parts[ index ] )
                if value < 0 or value > member_count:
                    failures.append( f"{og_id}: clade column '{header_columns[ index ].split(' (')[0]}' value {value} "
                                     f"out of range [0, {member_count}]" )

            # per annotation type
            for prefix, ( identifiers_index, names_index ) in type_indices.items():
                identifiers = [ token for token in parts[ identifiers_index ].split( U.DELIM ) if token ]
                names_cell = parts[ names_index ]

                if identifiers != sorted( identifiers ):
                    failures.append( f"{og_id}: {prefix}_Identifiers not sorted" )
                if len( identifiers ) != len( set( identifiers ) ):
                    failures.append( f"{og_id}: {prefix}_Identifiers contain duplicates" )
                if prefix in NAMES_BLANK_PREFIXES:
                    if names_cell != '':
                        failures.append( f"{og_id}: {prefix}_Names must be blank but is {names_cell!r}" )
                else:
                    names = [ token for token in names_cell.split( U.NAME_DELIM ) if token ] if names_cell else []
                    if len( identifiers ) != len( names ):
                        failures.append( f"{og_id}: {prefix} #identifiers {len( identifiers )} != #names {len( names )}" )

            if len( failures ) > 200:
                failures.append( "... (further failures suppressed; fix the above first)" )
                break

    input_orthogroup_count = count_input_orthogroups( orthogroups_path )
    check( data_rows == input_orthogroup_count, "Output rows == input orthogroups",
           f"table {data_rows} vs input {input_orthogroup_count}" )
    check( duplicate_orthogroups == 0, "Orthogroup_ID values unique",
           f"{duplicate_orthogroups} duplicate(s)" )

    status = "PASS" if not failures else "FAIL"
    report_lines = [
        status,
        "=" * 70,
        "GIGANTIC integrator - orthogroups_X_all_annotations validation report",
        "=" * 70,
        "",
        f"Output table: {table_path}",
        f"Data rows: {data_rows}",
        f"Input orthogroups: {input_orthogroup_count}",
        f"Species (tip) columns: {number_of_tips}",
        f"Full-coverage (root) clade columns: {len( full_coverage_indices )}",
        f"Total clade columns: {len( clade_column_indices )}",
        f"Annotation types: {', '.join( type_prefixes )}",
        "",
        "## Named checks",
        "",
    ]
    for ok, description, detail in checks:
        report_lines.append( f"[{'PASS' if ok else 'FAIL'}] {description} ({detail})" )
    if failures:
        report_lines.extend( [ "", "## Failures", "" ] )
        report_lines.extend( failures )
    report_lines.extend( [ "", "=" * 70 ] )

    report_path.write_text( '\n'.join( report_lines ) + '\n' )
    print( f"[002] validation {status}: {len( failures )} failure(s) -> {report_path}" )

    if failures:
        sys.exit( 1 )


if __name__ == '__main__':
    main()
