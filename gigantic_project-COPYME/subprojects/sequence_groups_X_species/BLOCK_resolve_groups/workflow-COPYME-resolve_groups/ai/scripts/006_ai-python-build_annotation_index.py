# AI: Claude Code | Opus 4.8 | 2026 July 11 | Purpose: Build ONE cross-producer sequence -> annotation index (PFAM, PANTHER, GO, Gene_Families, Gene_Groups) consumed by Script 004 to annotate the composite-clades detail tables
# Human: Eric Edsinger

"""
Script 006 — Build the cross-producer sequence -> annotation index.

Runs ONCE per workflow (not per producer). Produces a single table mapping each
annotated member sequence to its annotation identifiers + names for five modes:

    PFAM, PANTHER, GO           -- from the FEATURE-type annogroups (the raw
                                   per-sequence accession + its description) already
                                   produced by the annogroups subproject.
    Gene_Families, Gene_Groups  -- from the gene_families / gene_groups AGS FASTAs
                                   (the family/group slug is both identifier and name;
                                   the slug matches each producer's own SequenceGroup_ID).

Script 004 loads this index and, for every producer's composite-clades DETAIL tables,
adds per-sequence-group annotation columns aggregated (distinct union) over ALL of the
group's member sequences (Leonid, 2026-07).

Output (annotation_index/6_ai-sequence_annotation_index.tsv), one row per annotated
sequence (columns: Sequence_Identifier + <Mode>_Identifiers/<Mode>_Names x 5):
  identifiers are comma delimited (gigantic_conventions §34); names are ' // '
  delimited (names carry commas) and aligned position-for-position to the identifiers.

Fail-fast (§36): exits 1 on any missing configured source, or if the index is empty
(every configured source contributed zero rows -> a path/format problem, not biology).

Design note (research integrity): PFAM/PANTHER/GO come from feature annogroups, so a
sequence whose id was truncated upstream by InterProScan (255-char limit) simply has
no annotation here (a false NEGATIVE, never a false positive) — consistent with the
annogroup producers this workflow already resolves.
"""

import argparse
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_sequence_groups as U

# In-column identifier delimiter is the bare comma (§34); names carry commas, so the
# aligned *_Names columns use ' // ' instead.
IDENTIFIER_DELIM = U.DELIM
NAME_DELIM = ' // '

# The five annotation modes, in output order. Each contributes two columns:
# <mode>_Identifiers and <mode>_Names.
ANNOTATION_MODES = [ "PFAM", "PANTHER", "GO", "Gene_Families", "Gene_Groups" ]


def load_001_readers():
    """
    Import the gene_families / gene_groups readers from Script 001 (whose filename is
    not a valid module name) so the index derives EXACTLY the same SequenceGroup_ID
    slugs each producer emits.
    """
    script_path = Path( __file__ ).parent / "001_ai-python-adapt_sequence_group_membership.py"
    spec = importlib.util.spec_from_file_location( "adapt_membership_001", script_path )
    module = importlib.util.module_from_spec( spec )
    spec.loader.exec_module( module )
    return module.read_gene_families, module.read_gene_groups


def load_feature_annogroup_definitions( map_path: Path ):
    """
    From an annogroup map, the FEATURE-type annogroups only:
        annogroup_id -> ( accession, name )
    accession is the single Defining_Features accession; name is the source signature
    description (the text before ' ==' in Annotation_Definitions; '' when absent).
    """
    # Annogroup_ID (...)	Source (...)	Annogroup_Type (...)	Defining_Features (...)	Annotation_Definitions (...)	...
    # annogroup_pfam_PF00001	pfam	feature	PF00001	7 transmembrane receptor (rhodopsin family) ==PF00001	...
    feature_annogroups___accession_names = {}
    with open( map_path, 'r' ) as input_map:
        header_ids___indices = U.build_header_index( input_map.readline() )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_defining = header_ids___indices[ "Defining_Features" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_type ] != "feature":
                continue
            accession = parts[ index_defining ].strip()
            if not accession:
                continue
            definitions = parts[ index_definitions ] if index_definitions < len( parts ) else ''
            name = definitions.split( ' ==' )[ 0 ].strip() if definitions else ''
            feature_annogroups___accession_names[ parts[ index_annogroup ] ] = ( accession, name )
    return feature_annogroups___accession_names


def add_feature_annogroup_annotations( membership_path: Path, feature_annogroups___accession_names,
                                       sequences___ids_names ):
    """
    Stream an annogroup membership; for each ( sequence, feature annogroup ) add the
    feature's ( accession, name ) to sequences___ids_names[ sequence ] (a dict
    accession -> name, so an accession is recorded once with its canonical name).
    """
    # Sequence_Identifier (...)	Genus_Species (...)	Annogroup_ID (...)	Annogroup_Type (...)	...
    rows_added = 0
    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ index_annogroup ]
            accession_name = feature_annogroups___accession_names.get( annogroup_id )
            if accession_name is None:
                continue
            accession, name = accession_name
            sequences___ids_names[ parts[ index_sequence ] ][ accession ] = name
            rows_added += 1
    return rows_added


def add_slug_annotations( reader, source_root: Path, sequences___ids_names ):
    """
    From a gene_families / gene_groups reader ( yields ( group_id, sequence_id,
    genus_species ) ), record the slug as BOTH identifier and name for each sequence.
    """
    rows_added = 0
    for ( group_id, sequence_id, genus_species ) in reader( source_root ):
        sequences___ids_names[ sequence_id ][ group_id ] = group_id
        rows_added += 1
    return rows_added


def format_ids_names( ids_names: dict ):
    """Return ( identifiers_cell, names_cell ) for one sequence+mode: identifiers comma
    delimited (sorted, distinct); names ' // ' delimited, aligned to the identifiers."""
    identifiers = sorted( ids_names.keys() )
    names = [ ids_names[ identifier ] for identifier in identifiers ]
    return ( IDENTIFIER_DELIM.join( identifiers ), NAME_DELIM.join( names ) )


def main():
    parser = argparse.ArgumentParser( description = "Build the cross-producer sequence -> annotation index" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )   # OUTPUT_pipeline base
    parser.add_argument( '--workflow_root', default = None )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = Path( args.workflow_root ).resolve() if args.workflow_root else U.workflow_root_from_output_dir( args.output_dir )

    sources = config.get( "annotation_index" )
    if not sources:
        print( "CRITICAL ERROR: config is missing the 'annotation_index' block", file = sys.stderr )
        sys.exit( 1 )

    required_keys = [ "pfam_membership", "pfam_map", "panther_membership", "panther_map",
                      "go_membership", "go_map", "gene_families_dir", "gene_groups_dir" ]
    resolved = {}
    for key in required_keys:
        if key not in sources or not str( sources[ key ] ).strip():
            print( f"CRITICAL ERROR: annotation_index.{key} is not set", file = sys.stderr )
            sys.exit( 1 )
        path = U.resolve_input_path( workflow_root, str( sources[ key ] ).strip() )
        if not path.exists():
            print( f"CRITICAL ERROR: annotation_index.{key} not found: {path}", file = sys.stderr )
            sys.exit( 1 )
        resolved[ key ] = path

    read_gene_families, read_gene_groups = load_001_readers()

    # Per-mode: sequence_id -> { identifier: name }
    modes___sequences = { mode: defaultdict( dict ) for mode in ANNOTATION_MODES }

    # ---- PFAM / PANTHER / GO : feature-type annogroup accessions + descriptions ----
    for mode, membership_key, map_key in [
        ( "PFAM", "pfam_membership", "pfam_map" ),
        ( "PANTHER", "panther_membership", "panther_map" ),
        ( "GO", "go_membership", "go_map" ),
    ]:
        feature_definitions = load_feature_annogroup_definitions( resolved[ map_key ] )
        rows = add_feature_annogroup_annotations( resolved[ membership_key ], feature_definitions,
                                                  modes___sequences[ mode ] )
        print( f"[006] {mode}: {len( feature_definitions )} feature annogroups -> "
               f"{rows} sequence-feature rows over {len( modes___sequences[ mode ] )} sequences" )

    # ---- Gene_Families / Gene_Groups : the AGS slug (identifier == name) ----
    rows = add_slug_annotations( read_gene_families, resolved[ "gene_families_dir" ], modes___sequences[ "Gene_Families" ] )
    print( f"[006] Gene_Families: {rows} sequence rows over {len( modes___sequences[ 'Gene_Families' ] )} sequences" )
    rows = add_slug_annotations( read_gene_groups, resolved[ "gene_groups_dir" ], modes___sequences[ "Gene_Groups" ] )
    print( f"[006] Gene_Groups: {rows} sequence rows over {len( modes___sequences[ 'Gene_Groups' ] )} sequences" )

    # ---- write one row per annotated sequence (union of sequences across modes) ----
    all_sequences = set()
    for mode in ANNOTATION_MODES:
        all_sequences.update( modes___sequences[ mode ].keys() )
    if not all_sequences:
        print( "CRITICAL ERROR: annotation index is empty (no sequence carried any annotation in any mode) "
               "-- check the annotation_index source paths/formats", file = sys.stderr )
        sys.exit( 1 )

    output_dir = Path( args.output_dir ) / "annotation_index"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_path = output_dir / "6_ai-sequence_annotation_index.tsv"

    header = [ "Sequence_Identifier (full GIGANTIC member sequence identifier)" ]
    for mode in ANNOTATION_MODES:
        header.append( f"{mode}_Identifiers (comma delimited distinct {mode} identifiers carried by this sequence)" )
        header.append( f"{mode}_Names (' // ' delimited {mode} names aligned to {mode}_Identifiers)" )

    rows_written = 0
    with open( output_path, 'w' ) as output_file:
        output_file.write( '\t'.join( header ) + '\n' )
        for sequence_id in sorted( all_sequences ):
            cells = [ sequence_id ]
            for mode in ANNOTATION_MODES:
                ids_names = modes___sequences[ mode ].get( sequence_id, {} )
                identifiers_cell, names_cell = format_ids_names( ids_names )
                cells.append( identifiers_cell )
                cells.append( names_cell )
            output_file.write( '\t'.join( cells ) + '\n' )
            rows_written += 1

    print( f"[006] wrote annotation index: {rows_written} annotated sequences x {len( ANNOTATION_MODES )} modes -> {output_path}" )


if __name__ == '__main__':
    main()
