#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Validate the annotations_X_orthogroups integration tables (strict fail-fast, §36)
# Human: Eric Edsinger

"""
Script 004 — Validation (strict fail-fast per gigantic_conventions §36).

Cross-checks the three output tables for internal consistency. ANY failure
writes a FAIL report and exits 1 (research-integrity: a silent join artifact in
published results is unacceptable, per AI_BEHAVIOR.md).

Checks:
  1. Composition_Class is one of the four valid classes for every orthogroup,
     and the Qualifies flag agrees with the class.
  1b. The metazoan phylum overlay is well-formed: Metazoan_Phylum_Signature uses
     only known phyla, Has_NonMetazoan is yes/no, and the signature is consistent
     with the coarse Composition_Class.
  2. Table 2 row count == count of non_bilaterian_metazoan rows in the
     composition table, and every Table 2 orthogroup is classified
     non_bilaterian_metazoan.
  3. Table 1 referential integrity: every orthogroup ID referenced in Table 1
     exists in the composition table.
  4. Table 1 internal arithmetic per row:
       - the four coarse per-class counts sum to Orthogroup_Count
       - each per-class ID-list length == its per-class count
       - Members_With + Members_Without == Annogroup_Member_Protein_Count
  5. Table 1 keep-rule: every retained annogroup has
     NonBilaterian_Metazoan_Orthogroup_Count >= 1.
  6. Table 1 named phylum-composition columns: each named _IDs length == its
     _Count; every named ID is in All_Orthogroup_IDs and actually resolves to that
     named class (via the Script 001 signature); the named classes are disjoint so
     their counts sum to <= Orthogroup_Count.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U

VALID_CLASSES = { "bilaterian_only", "mixed_with_bilaterian", "non_bilaterian_metazoan", "non_metazoan_only" }
QUALIFYING_CLASS = "non_bilaterian_metazoan"


def split_cell( cell: str ) -> list:
    return [ token for token in cell.split( U.DELIM ) if token ]


def main():
    parser = argparse.ArgumentParser( description = "Validate annotations_X_orthogroups results (fail-fast)" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    output_base = Path( args.output_dir )
    composition_path = U.resolve_composition_table_path( output_base )
    table2_path = U.resolve_timestamped_output_path( output_base / "2-output", "2_ai-nonbilaterian_metazoan_orthogroups", output_base )
    table1_path = U.resolve_timestamped_output_path( output_base / "3-output", "3_ai-annogroups_X_orthogroups", output_base )

    failures = []

    for required in ( composition_path, table2_path, table1_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required table not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    # ---- load composition: orthogroup -> class + phylum signature -------------
    orthogroups___classes = {}
    orthogroups___named_class = {}   # orthogroup_id -> named phylum class (or None)
    composition_qualifying_count = 0
    valid_phyla = set( U.METAZOAN_PHYLA )
    with open( composition_path, 'r' ) as input_composition:
        header_ids___indices = U.build_header_index( input_composition.readline() )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_class = header_ids___indices[ "Composition_Class" ]
        index_qualifies = header_ids___indices[ "Qualifies_NonBilaterian_Metazoan" ]
        index_signature = header_ids___indices[ "Metazoan_Phylum_Signature" ]
        index_has_nonmeta = header_ids___indices[ "Has_NonMetazoan" ]
        for line in input_composition:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ index_og ]
            composition_class = parts[ index_class ]
            qualifies = parts[ index_qualifies ]
            orthogroups___classes[ orthogroup_id ] = composition_class
            if composition_class not in VALID_CLASSES:
                failures.append( f"Check 1: orthogroup {orthogroup_id} has invalid Composition_Class '{composition_class}'" )
            expected_qualifies = "yes" if composition_class == QUALIFYING_CLASS else "no"
            if qualifies != expected_qualifies:
                failures.append( f"Check 1: orthogroup {orthogroup_id} Qualifies='{qualifies}' disagrees with class '{composition_class}'" )
            if composition_class == QUALIFYING_CLASS:
                composition_qualifying_count += 1

            # Check 1b: phylum signature is well-formed and consistent with the
            # coarse class; resolve and cache the named phylum class for Check 6.
            signature_cell = parts[ index_signature ]
            has_nonmeta_cell = parts[ index_has_nonmeta ]
            signature = U.parse_signature_cell( signature_cell )
            stray_tokens = signature - valid_phyla
            if stray_tokens:
                failures.append( f"Check 1b: orthogroup {orthogroup_id} signature has unknown phyla {sorted( stray_tokens )}" )
            if has_nonmeta_cell not in ( "yes", "no" ):
                failures.append( f"Check 1b: orthogroup {orthogroup_id} Has_NonMetazoan='{has_nonmeta_cell}' is not yes/no" )
            has_nonmetazoan = ( has_nonmeta_cell == "yes" )
            # Signature must be consistent with the coarse class.
            non_bilaterian_present = bool( signature & U.NON_BILATERIAN_PHYLA )
            bilaterian_present = ( "Bilateria" in signature )
            if composition_class == "non_metazoan_only" and signature:
                failures.append( f"Check 1b: orthogroup {orthogroup_id} class non_metazoan_only but signature '{signature_cell}' is non-empty" )
            if composition_class == "bilaterian_only" and signature != frozenset( { "Bilateria" } ):
                failures.append( f"Check 1b: orthogroup {orthogroup_id} class bilaterian_only but signature '{signature_cell}' != Bilateria" )
            if composition_class == "non_bilaterian_metazoan" and ( bilaterian_present or not non_bilaterian_present ):
                failures.append( f"Check 1b: orthogroup {orthogroup_id} class non_bilaterian_metazoan but signature '{signature_cell}' is inconsistent" )
            orthogroups___named_class[ orthogroup_id ] = U.named_phylum_class( signature, has_nonmetazoan )

    # ---- Table 2 ------------------------------------------------------------
    table2_row_count = 0
    with open( table2_path, 'r' ) as input_table2:
        header_ids___indices = U.build_header_index( input_table2.readline() )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        for line in input_table2:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            table2_row_count += 1
            orthogroup_id = parts[ index_og ]
            if orthogroups___classes.get( orthogroup_id ) != QUALIFYING_CLASS:
                failures.append( f"Check 2: Table 2 orthogroup {orthogroup_id} is not classified {QUALIFYING_CLASS} in composition table" )

    if table2_row_count != composition_qualifying_count:
        failures.append(
            f"Check 2: Table 2 row count ({table2_row_count}) != {QUALIFYING_CLASS} count in composition table ({composition_qualifying_count})"
        )

    # ---- Table 1 ------------------------------------------------------------
    table1_row_count = 0
    with open( table1_path, 'r' ) as input_table1:
        header_ids___indices = U.build_header_index( input_table1.readline() )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_member_count = header_ids___indices[ "Annogroup_Member_Protein_Count" ]
        index_with = header_ids___indices[ "Members_With_Orthogroup_Count" ]
        index_without = header_ids___indices[ "Members_Without_Orthogroup_Count" ]
        index_og_count = header_ids___indices[ "Orthogroup_Count" ]
        index_qual_count = header_ids___indices[ "NonBilaterian_Metazoan_Orthogroup_Count" ]
        index_unicell_count = header_ids___indices[ "NonMetazoan_Only_Orthogroup_Count" ]
        index_bil_count = header_ids___indices[ "Bilaterian_Only_Orthogroup_Count" ]
        index_mixed_count = header_ids___indices[ "Mixed_With_Bilaterian_Orthogroup_Count" ]
        index_qual_ids = header_ids___indices[ "NonBilaterian_Metazoan_Orthogroup_IDs" ]
        index_unicell_ids = header_ids___indices[ "NonMetazoan_Only_Orthogroup_IDs" ]
        index_bil_ids = header_ids___indices[ "Bilaterian_Only_Orthogroup_IDs" ]
        index_mixed_ids = header_ids___indices[ "Mixed_With_Bilaterian_Orthogroup_IDs" ]
        index_all_ids = header_ids___indices[ "All_Orthogroup_IDs" ]

        # Named phylum-composition columns (count + IDs per class).
        named_class___count_index = {}
        named_class___ids_index = {}
        for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS:
            named_class___count_index[ class_key ] = header_ids___indices[ f"{class_key}_Orthogroup_Count" ]
            named_class___ids_index[ class_key ] = header_ids___indices[ f"{class_key}_Orthogroup_IDs" ]

        for line in input_table1:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            table1_row_count += 1
            annogroup_id = parts[ index_annogroup ]

            qual_count = int( parts[ index_qual_count ] )
            unicell_count = int( parts[ index_unicell_count ] )
            bil_count = int( parts[ index_bil_count ] )
            mixed_count = int( parts[ index_mixed_count ] )
            og_count = int( parts[ index_og_count ] )
            member_count = int( parts[ index_member_count ] )
            with_count = int( parts[ index_with ] )
            without_count = int( parts[ index_without ] )

            qual_ids = split_cell( parts[ index_qual_ids ] )
            unicell_ids = split_cell( parts[ index_unicell_ids ] )
            bil_ids = split_cell( parts[ index_bil_ids ] )
            mixed_ids = split_cell( parts[ index_mixed_ids ] )
            all_ids = split_cell( parts[ index_all_ids ] )

            # Check 5: keep-rule
            if qual_count < 1:
                failures.append( f"Check 5: annogroup {annogroup_id} retained with NonBilaterian_Metazoan_Orthogroup_Count {qual_count} (< 1)" )

            # Check 4: arithmetic
            if qual_count + unicell_count + bil_count + mixed_count != og_count:
                failures.append( f"Check 4: annogroup {annogroup_id} class counts {qual_count}+{unicell_count}+{bil_count}+{mixed_count} != Orthogroup_Count {og_count}" )
            if with_count + without_count != member_count:
                failures.append( f"Check 4: annogroup {annogroup_id} members {with_count}+{without_count} != Member_Protein_Count {member_count}" )
            if ( len( qual_ids ) != qual_count or len( unicell_ids ) != unicell_count
                 or len( bil_ids ) != bil_count or len( mixed_ids ) != mixed_count ):
                failures.append( f"Check 4: annogroup {annogroup_id} ID-list lengths do not match per-class counts" )
            if len( all_ids ) != og_count:
                failures.append( f"Check 4: annogroup {annogroup_id} All_Orthogroup_IDs length {len( all_ids )} != Orthogroup_Count {og_count}" )

            # Check 3: referential integrity
            for orthogroup_id in all_ids:
                if orthogroup_id not in orthogroups___classes:
                    failures.append( f"Check 3: annogroup {annogroup_id} references orthogroup {orthogroup_id} absent from composition table" )

            # Check 6: named phylum-composition columns.
            #   - each named _IDs length == its _Count
            #   - every named ID appears in All_Orthogroup_IDs (subset)
            #   - every named ID actually resolves to that named class (Script 001
            #     signature -> U.named_phylum_class), no misassignment
            #   - the named classes are disjoint and a subset of the orthogroups,
            #     so their counts sum to <= Orthogroup_Count
            all_ids_set = set( all_ids )
            named_total = 0
            for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS:
                named_count = int( parts[ named_class___count_index[ class_key ] ] )
                named_ids = split_cell( parts[ named_class___ids_index[ class_key ] ] )
                named_total += named_count
                if len( named_ids ) != named_count:
                    failures.append( f"Check 6: annogroup {annogroup_id} {class_key}_Orthogroup_IDs length {len( named_ids )} != count {named_count}" )
                for orthogroup_id in named_ids:
                    if orthogroup_id not in all_ids_set:
                        failures.append( f"Check 6: annogroup {annogroup_id} {class_key} references orthogroup {orthogroup_id} not in All_Orthogroup_IDs" )
                    elif orthogroups___named_class.get( orthogroup_id ) != class_key:
                        failures.append( f"Check 6: annogroup {annogroup_id} orthogroup {orthogroup_id} listed under {class_key} but its signature resolves to {orthogroups___named_class.get( orthogroup_id )}" )
            if named_total > og_count:
                failures.append( f"Check 6: annogroup {annogroup_id} named phylum-class counts sum {named_total} > Orthogroup_Count {og_count} (classes must be disjoint)" )

    # ---- report -------------------------------------------------------------
    output_dir = output_base / "4-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_report_path = output_dir / "4_ai-validation_report.txt"

    status = "PASS" if not failures else "FAIL"
    report_lines = [
        "=" * 78,
        "GIGANTIC integrator - annotations_X_orthogroups - VALIDATION REPORT",
        "=" * 78,
        "",
        f"Status: {status}",
        "",
        f"Orthogroups classified:                {len( orthogroups___classes )}",
        f"  qualifying (non_bilaterian_metazoan): {composition_qualifying_count}",
        f"Table 2 rows (qualifying orthogroups):  {table2_row_count}",
        f"Table 1 rows (kept annogroups):        {table1_row_count}",
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

    print( f"[004] validation {status} -> {output_report_path}" )

    if failures:
        print( f"CRITICAL ERROR: validation FAILED with {len( failures )} issue(s). See {output_report_path}", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
