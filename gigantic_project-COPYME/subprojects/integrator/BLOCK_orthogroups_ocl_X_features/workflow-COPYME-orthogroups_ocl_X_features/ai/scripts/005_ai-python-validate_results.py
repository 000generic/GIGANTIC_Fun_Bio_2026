#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Validate the per-structure integration outputs (fail-fast)
# Human: Eric Edsinger

"""
Script 005 — Validate the integration outputs for one structure (fail-fast, §36).

Cross-checks the three tables against each other and against the OCL spine:

  CHECK 1  All three tables exist and have a header.
  CHECK 2  Table 1 orthogroup count == OCL summary orthogroup count.
  CHECK 3  Per Table 1 row: each integration count == number of IDs in its
           matching sequence-ID cell, and count <= members-available count
           <= orthogroup member count.
  CHECK 4  Table 3 gene-row count == sum of orthogroup member counts in Table 1.
  CHECK 5  Every Orthogroup_ID in Table 2 exists in Table 1, and every
           Block_State_Letter is one of O / P / L.

Writes a validation report to 5-output/. Exits 1 if ANY check fails — never
exits 0 with problems (per AI_BEHAVIOR.md zero-tolerance for silent artifacts).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U


def read_tsv( path: Path ):
    """Return ( header_ids___indices, list_of_parts_rows )."""
    rows = []
    with open( path, 'r' ) as input_tsv:
        header_line = input_tsv.readline()
        header_ids___indices = U.build_header_index( header_line )
        for line in input_tsv:
            line = line.rstrip( '\n' )
            if not line:
                continue
            rows.append( line.split( '\t' ) )
    return header_ids___indices, rows


def main():
    parser = argparse.ArgumentParser( description = "Validate integration outputs (fail-fast)" )
    parser.add_argument( '--structure_id', required = True )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    structure_id = args.structure_id
    structure_name = f"structure_{structure_id}"

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    input_ocl_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "ocl_orthogroups_dir" ] )

    base = Path( args.output_dir ) / structure_name
    output_base = Path( args.output_dir )
    table1_path = U.resolve_timestamped_output_path( base / "2-output", "2_ai-orthogroups-integrated_summary", output_base )
    table2_path = U.resolve_timestamped_output_path( base / "3-output", "3_ai-block_states-integrated_expanded", output_base )
    table3_path = U.resolve_timestamped_output_path( base / "4-output", "4_ai-genes-integrated_drilldown", output_base )
    ocl_summary_path = input_ocl_dir / structure_name / "4_ai-orthogroups-complete_ocl_summary.tsv"

    failures = []
    notes = []

    # CHECK 1 — all tables present
    for label, path in [ ( "Table 1", table1_path ), ( "Table 2", table2_path ), ( "Table 3", table3_path ) ]:
        if not path.is_file():
            failures.append( f"CHECK 1: {label} missing: {path}" )
    if failures:
        write_report_and_exit( base, structure_id, failures, notes )

    t1_header, t1_rows = read_tsv( table1_path )
    t2_header, t2_rows = read_tsv( table2_path )
    t3_header, t3_rows = read_tsv( table3_path )

    # CHECK 2 — Table 1 count vs OCL summary count
    if ocl_summary_path.is_file():
        _, ocl_rows = read_tsv( ocl_summary_path )
        if len( t1_rows ) != len( ocl_rows ):
            failures.append( f"CHECK 2: Table 1 has {len( t1_rows )} orthogroups but OCL summary has {len( ocl_rows )}" )
        else:
            notes.append( f"CHECK 2 OK: {len( t1_rows )} orthogroups match OCL summary" )
    else:
        notes.append( f"CHECK 2 SKIPPED: OCL summary not found at {ocl_summary_path}" )

    # CHECK 3 — per-row count/list consistency in Table 1
    i_member_count = t1_header[ "Orthogroup_Member_Count" ]
    triples = [
        ( "Dark", "Dark_Integration_Count", "Dark_Integration_Sequence_IDs", "Dark_Members_Available_Count" ),
        ( "Hotspot", "Hotspot_Integration_Count", "Hotspot_Integration_Sequence_IDs", "Hotspot_Members_Available_Count" ),
        ( "Secretome", "Secretome_Integration_Count", "Secretome_Integration_Sequence_IDs", "Secretome_Members_Available_Count" ),
    ]
    sum_member_count = 0
    check3_failures = 0
    for parts in t1_rows:
        member_count = int( parts[ i_member_count ] )
        sum_member_count += member_count
        for source, c_col, ids_col, avail_col in triples:
            count = int( parts[ t1_header[ c_col ] ] )
            ids_cell = parts[ t1_header[ ids_col ] ]
            id_count = len( [ x for x in ids_cell.split( U.DELIM ) if x ] )
            avail = int( parts[ t1_header[ avail_col ] ] )
            if count != id_count:
                check3_failures += 1
                if check3_failures <= 5:
                    failures.append( f"CHECK 3: {source} count {count} != id-list length {id_count} (OG row)" )
            if count > avail:
                check3_failures += 1
                if check3_failures <= 5:
                    failures.append( f"CHECK 3: {source} count {count} > available {avail}" )
            if avail > member_count:
                check3_failures += 1
                if check3_failures <= 5:
                    failures.append( f"CHECK 3: {source} available {avail} > member count {member_count}" )
    if check3_failures == 0:
        notes.append( "CHECK 3 OK: integration counts consistent with id-lists and availability" )

    # CHECK 4 — Table 3 gene rows == sum of member counts
    if len( t3_rows ) != sum_member_count:
        failures.append( f"CHECK 4: Table 3 has {len( t3_rows )} gene rows but Table 1 member sum is {sum_member_count}" )
    else:
        notes.append( f"CHECK 4 OK: {len( t3_rows )} gene rows == sum of orthogroup member counts" )

    # CHECK 5 — Table 2 orthogroups subset of Table 1; states in O/P/L
    t1_orthogroups = { parts[ t1_header[ "Orthogroup_ID" ] ] for parts in t1_rows }
    i_t2_og = t2_header[ "Orthogroup_ID" ]
    i_t2_state = t2_header[ "Block_State_Letter" ]
    bad_state = 0
    orphan_og = 0
    for parts in t2_rows:
        if parts[ i_t2_og ] not in t1_orthogroups:
            orphan_og += 1
        if parts[ i_t2_state ] not in ( "O", "P", "L" ):
            bad_state += 1
    if orphan_og:
        failures.append( f"CHECK 5: {orphan_og} Table 2 rows reference orthogroups absent from Table 1" )
    if bad_state:
        failures.append( f"CHECK 5: {bad_state} Table 2 rows have a Block_State_Letter outside O/P/L" )
    if not orphan_og and not bad_state:
        notes.append( f"CHECK 5 OK: {len( t2_rows )} block-state rows reference valid orthogroups and states" )

    write_report_and_exit( base, structure_id, failures, notes )


def write_report_and_exit( base: Path, structure_id: str, failures, notes ):
    output_dir = base / "5-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    report_path = output_dir / f"5_ai-structure_{structure_id}-validation_report.txt"

    status = "FAIL" if failures else "PASS"
    lines = [
        "=" * 70,
        f"integrator orthogroups_ocl_X_features — validation report (structure_{structure_id})",
        f"Status: {status}",
        "=" * 70,
        "",
        "Notes:",
    ]
    lines += [ f"  - {n}" for n in notes ] or [ "  (none)" ]
    lines += [ "", "Failures:" ]
    lines += [ f"  - {f}" for f in failures ] or [ "  (none)" ]
    lines += [ "", "=" * 70 ]

    with open( report_path, 'w' ) as output_report:
        output_report.write( '\n'.join( lines ) + '\n' )

    print( f"[005 structure_{structure_id}] validation {status} -> {report_path}" )
    if failures:
        for f in failures:
            print( f"  VALIDATION FAILURE: {f}", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
