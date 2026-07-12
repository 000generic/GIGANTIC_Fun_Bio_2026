#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27 | Purpose: Fail-fast validation of the ambiguous_nodes_X_annogroups projections (research-integrity cross-checks)
# Human: Eric Edsinger

"""
Script 003 — Validation (fail-fast, per §36 + AI_BEHAVIOR.md zero-tolerance).

Cross-checks every projected table against the source deconvolution so a silent
projection error (a dropped annogroup, a fixed clade leaking in, a scope keeping
the wrong nodes) cannot reach research outputs. For each source x enabled scope:

  1. identity columns match the source all_structures identity columns exactly
     (same header text, same order);
  2. EVERY clade column in the projection is an ambiguous node (its header says
     'present in N of M structures' with N < M) — no fixed backbone clade leaked in;
  3. the projection's clade set is a subset of the global ambiguous-node set;
  4. one/some scope clade sets equal the ambiguous nodes actually carried by the
     chosen structure(s) — nothing missing, nothing extra;
  5. the projection has exactly as many annogroup rows as the source table
     (no annogroup dropped or duplicated);
  6. the Script 001 registry is consistent (ambiguous-node count + per-scope
     membership counts match the projections).

Writes 3-output/3_ai-validation_report.txt. Exits 1 on the FIRST failed check.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_ambiguous_nodes as U


def fail( report_lines: list, message: str, report_path: Path ) -> None:
    """Write the report with a FAILED status and exit 1."""
    report_lines.append( "" )
    report_lines.append( f"STATUS: FAILED — {message}" )
    report_path.parent.mkdir( parents = True, exist_ok = True )
    with open( report_path, 'w' ) as output_report:
        output_report.write( '\n'.join( report_lines ) + '\n' )
    print( f"CRITICAL ERROR: validation failed — {message}", file = sys.stderr )
    sys.exit( 1 )


def count_data_rows( path: Path ) -> int:
    """Count non-empty data rows (excludes the header line)."""
    with open( path, 'r' ) as input_file:
        input_file.readline()
        return sum( 1 for line in input_file if line.strip() )


def read_projection_header( path: Path ):
    """Return ( identity_header_texts, clades ) for a projected table."""
    with open( path, 'r' ) as input_file:
        header_line = input_file.readline().rstrip( '\n' )
    columns = header_line.split( '\t' )
    identity_indices, clades = U.parse_tree_counts_header( header_line )
    identity_texts = [ columns[ i ] for i in identity_indices ]
    return ( identity_texts, clades )


def main():
    parser = argparse.ArgumentParser( description = "Validate ambiguous_nodes_X_annogroups projections" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    output_base = Path( args.output_dir )
    report_path = output_base / "3-output" / "3_ai-validation_report.txt"

    scopes = config.get( "structure_scopes", {} )
    one_scope = scopes.get( "one", {} ) or {}
    scope_flags = {
        "all": bool( ( scopes.get( "all", {} ) or {} ).get( "enabled", True ) ),
        "one": bool( one_scope.get( "enabled", False ) ),
        "some": bool( ( scopes.get( "some", {} ) or {} ).get( "enabled", False ) ),
    }
    one_structure_id = str( one_scope.get( "structure_id", "" ) ).strip()

    sources = U.resolve_sources( workflow_root, config )
    some_structures = U.resolve_some_structures( workflow_root, config ) if scope_flags[ "some" ] else []

    report_lines = [
        "=" * 78,
        "GIGANTIC integrator — ambiguous_nodes_X_annogroups validation",
        "=" * 78,
        "",
        f"Sources: {', '.join( sources )}",
        f"Scopes enabled: " + ', '.join( name for name, on in scope_flags.items() if on ),
        "",
    ]

    for source in sources:
        all_structures_path = U.source_all_structures_path( workflow_root, config, source )
        with open( all_structures_path, 'r' ) as input_all_structures:
            header_line = input_all_structures.readline().rstrip( '\n' )
        columns = header_line.split( '\t' )
        identity_indices, clades = U.parse_tree_counts_header( header_line )
        source_identity_texts = [ columns[ i ] for i in identity_indices ]
        ambiguous_ids = { clade[ 'clade_id_name' ] for clade in clades if clade[ 'is_ambiguous' ] }
        source_rows = count_data_rows( all_structures_path )
        report_lines.append( f"[{source}] {len( ambiguous_ids )} ambiguous nodes; {source_rows} annogroups" )

        # Expected one/some ambiguous-node sets, from the per-structure files.
        expected_one = set()
        if scope_flags[ "one" ]:
            expected_one = ambiguous_ids & U.read_structure_clade_set(
                U.source_per_structure_path( workflow_root, config, source, one_structure_id ) )
        expected_some = set()
        if scope_flags[ "some" ]:
            for structure_id in some_structures:
                expected_some |= U.read_structure_clade_set(
                    U.source_per_structure_path( workflow_root, config, source, structure_id ) )
            expected_some &= ambiguous_ids

        expected_by_scope = { "all": ambiguous_ids, "one": expected_one, "some": expected_some }
        suffix_by_scope = { "all": "all_structures", "one": one_structure_id, "some": "some_structures" }

        for scope_name in ( "all", "one", "some" ):
            if not scope_flags[ scope_name ]:
                continue
            scope_path = U.resolve_timestamped_output_path(
                output_base / "2-output" / source / scope_name,
                f"2_ai-{source}-ambiguous_nodes_X_annogroups-{suffix_by_scope[ scope_name ]}",
                output_base,
            )
            if not scope_path.is_file():
                fail( report_lines, f"{source}/{scope_name}: projected table missing ({scope_path})", report_path )

            identity_texts, projection_clades = read_projection_header( scope_path )
            if identity_texts != source_identity_texts:
                fail( report_lines, f"{source}/{scope_name}: identity columns differ from the source table", report_path )

            projection_ids = []
            for clade in projection_clades:
                if not clade[ 'is_ambiguous' ]:
                    fail( report_lines, f"{source}/{scope_name}: fixed clade {clade[ 'clade_id_name' ]} leaked into the projection", report_path )
                projection_ids.append( clade[ 'clade_id_name' ] )
            projection_id_set = set( projection_ids )

            if len( projection_id_set ) != len( projection_ids ):
                fail( report_lines, f"{source}/{scope_name}: duplicate clade columns in the projection", report_path )
            if not projection_id_set.issubset( ambiguous_ids ):
                fail( report_lines, f"{source}/{scope_name}: projection has clades outside the global ambiguous set", report_path )
            if projection_id_set != expected_by_scope[ scope_name ]:
                missing = sorted( expected_by_scope[ scope_name ] - projection_id_set )[ :5 ]
                extra = sorted( projection_id_set - expected_by_scope[ scope_name ] )[ :5 ]
                fail( report_lines, f"{source}/{scope_name}: clade set mismatch (missing e.g. {missing}; extra e.g. {extra})", report_path )

            scope_rows = count_data_rows( scope_path )
            if scope_rows != source_rows:
                fail( report_lines, f"{source}/{scope_name}: {scope_rows} rows != {source_rows} source annogroups", report_path )

            report_lines.append( f"  [OK] {scope_name}: {len( projection_id_set )} ambiguous nodes x {scope_rows} annogroups" )

        # Registry consistency.
        registry_path = U.resolve_timestamped_output_path(
            output_base / "1-output" / source,
            f"1_ai-{source}-ambiguous_node_registry",
            output_base,
        )
        if not registry_path.is_file():
            fail( report_lines, f"{source}: ambiguous_node_registry missing", report_path )
        registry_ids = set()
        registry_in_one = 0
        registry_in_some = 0
        with open( registry_path, 'r' ) as input_registry:
            header_ids___indices = U.build_header_index( input_registry.readline() )
            index_clade = header_ids___indices[ "Clade_ID_Name" ]
            index_in_one = header_ids___indices[ "In_One_Scope" ]
            index_in_some = header_ids___indices[ "In_Some_Scope" ]
            for line in input_registry:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                registry_ids.add( parts[ index_clade ] )
                if parts[ index_in_one ] == "yes":
                    registry_in_one += 1
                if parts[ index_in_some ] == "yes":
                    registry_in_some += 1
        if registry_ids != ambiguous_ids:
            fail( report_lines, f"{source}: registry ambiguous nodes != deconvolution ambiguous nodes", report_path )
        if scope_flags[ "one" ] and registry_in_one != len( expected_one ):
            fail( report_lines, f"{source}: registry In_One_Scope count {registry_in_one} != {len( expected_one )}", report_path )
        if scope_flags[ "some" ] and registry_in_some != len( expected_some ):
            fail( report_lines, f"{source}: registry In_Some_Scope count {registry_in_some} != {len( expected_some )}", report_path )
        report_lines.append( f"  [OK] registry consistent ({len( registry_ids )} ambiguous nodes)" )

    report_lines.append( "" )
    report_lines.append( "STATUS: PASS — every cross-check held" )
    report_path.parent.mkdir( parents = True, exist_ok = True )
    with open( report_path, 'w' ) as output_report:
        output_report.write( '\n'.join( report_lines ) + '\n' )
    print( f"[003] validation PASS -> {report_path}" )


if __name__ == '__main__':
    main()
