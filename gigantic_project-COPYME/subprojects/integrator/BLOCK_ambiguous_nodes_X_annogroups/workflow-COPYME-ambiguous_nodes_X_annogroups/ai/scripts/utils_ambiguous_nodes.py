# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27 | Purpose: Shared helpers for the ambiguous_nodes_X_annogroups integration scripts
# Human: Eric Edsinger

"""
Shared helpers for the integrator ambiguous_nodes_X_annogroups pipeline.

Provides:
  - load_config / workflow_root_from_output_dir / resolve_input_path : YAML config + path resolution
  - build_header_index               : self-documenting-header column lookup
  - parse_tree_counts_header         : split a deconvolution header into identity
                                       columns + clade columns (with structure counts)
  - parse_clade_column_header        : (clade_id_name, present_count, total_count)
                                       from one deconvolution clade column header
  - resolve_sources                  : "all" -> sources exposed for this species set
  - read_structure_clade_set         : the clade_id_names that are columns in one
                                       per-structure tree-counts file (header only)
  - resolve_some_structures          : union of the inline + file "some" structure ids
  - DELIM                            : in-column list delimiter (bare comma, §34)

All scripts in this workflow import this module via:
    sys.path.insert( 0, str( Path( __file__ ).parent ) )
    import utils_ambiguous_nodes
"""

import re
import sys
from pathlib import Path
import yaml

# In-column multi-value delimiter — bare comma per gigantic_conventions §34.
DELIM = ','

# A deconvolution clade column documents itself as "... present in N of M structures".
# This is the load-bearing signal: a clade is an AMBIGUOUS node iff N < M.
PRESENT_IN_PATTERN = re.compile( r'present in (\d+) of (\d+) structures' )
# Tips carry "= species X"; internal nodes carry "K descendant species". Optional.
DESCENDANT_COUNT_PATTERN = re.compile( r'(\d+) descendant species' )

# The per-source deconvolution file names (annogroups subproject, script 004).
TREE_COUNTS_ALL_STRUCTURES = "4_ai-{source}-annogroup_tree_counts-all_structures.tsv"
TREE_COUNTS_PER_STRUCTURE_DIR = "annogroup_tree_counts_per_structure"
TREE_COUNTS_PER_STRUCTURE = "4_ai-{source}-annogroup_tree_counts-{structure}.tsv"


def load_config( config_path: str ) -> dict:
    """Load the START_HERE-user_config.yaml into a nested dict."""
    with open( config_path, 'r' ) as input_config:
        config = yaml.safe_load( input_config )
    return config


def workflow_root_from_output_dir( output_dir: str ) -> Path:
    """
    The workflow root is the parent of OUTPUT_pipeline. Input paths in the YAML
    are written relative to the workflow root (per gigantic_conventions §5).
    """
    return Path( output_dir ).resolve().parent


def resolve_input_path( workflow_root: Path, relative_path: str ) -> Path:
    """Resolve a YAML-relative input path against the workflow root."""
    return ( workflow_root / relative_path ).resolve()


def build_header_index( header_line: str ) -> dict:
    """
    Map self-documenting header IDs to column indices.

    GIGANTIC TSV headers look like 'Annogroup_ID (annogroup identifier ...)';
    the header_ID is the text before ' (' . Returns { header_ID : index }.
    """
    header_ids___indices = {}
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    for index, column in enumerate( parts_header_line ):
        header_id = column.split( ' (' )[ 0 ].strip()
        header_ids___indices[ header_id ] = index
    return header_ids___indices


def parse_clade_column_header( column_header: str ):
    """
    Parse one deconvolution clade column header.

    Returns ( clade_id_name, present_count, total_count ) when the header is a
    clade column (it documents 'present in N of M structures'), else None (the
    leading annogroup-identity columns: Annogroup_ID, Source, Species_List, ...).

    Example clade header:
      'C087_Metazoa_Subclade_1 (member-protein count of this annogroup within
       clade C087_Metazoa_Subclade_1; 51 descendant species; present in 1 of 105
       structures)'
    """
    match = PRESENT_IN_PATTERN.search( column_header )
    if match is None:
        return None
    clade_id_name = column_header.split( ' (' )[ 0 ].strip()
    present_count = int( match.group( 1 ) )
    total_count = int( match.group( 2 ) )
    return ( clade_id_name, present_count, total_count )


def parse_descendant_species_count( column_header: str ) -> int:
    """Descendant-species count embedded in a clade column header (0 if a tip / absent)."""
    match = DESCENDANT_COUNT_PATTERN.search( column_header )
    return int( match.group( 1 ) ) if match else 0


def parse_tree_counts_header( header_line: str ) -> tuple:
    """
    Split a deconvolution header line into identity columns and clade columns.

    Returns ( identity_indices, clades ):
      - identity_indices : list of column indices for the leading annogroup-identity
                           columns (everything that is NOT a clade column), in order
      - clades           : list of dicts, one per clade column, in column order:
                           { 'index', 'clade_id_name', 'present_count',
                             'total_count', 'descendant_species_count',
                             'is_ambiguous' }  (is_ambiguous == present < total)
    """
    identity_indices = []
    clades = []
    columns = header_line.rstrip( '\n' ).split( '\t' )
    for index, column in enumerate( columns ):
        parsed = parse_clade_column_header( column )
        if parsed is None:
            identity_indices.append( index )
            continue
        clade_id_name, present_count, total_count = parsed
        clades.append( {
            'index': index,
            'clade_id_name': clade_id_name,
            'present_count': present_count,
            'total_count': total_count,
            'descendant_species_count': parse_descendant_species_count( column ),
            'is_ambiguous': present_count < total_count,
        } )
    return ( identity_indices, clades )


def source_species_dir( workflow_root: Path, config: dict ) -> Path:
    """<annogroups_dir>/<species_set_name>/ resolved to an absolute path."""
    annogroups_dir = resolve_input_path( workflow_root, config[ "inputs" ][ "annogroups_dir" ] )
    return annogroups_dir / config[ "species_set_name" ]


def source_all_structures_path( workflow_root: Path, config: dict, source: str ) -> Path:
    """The all_structures deconvolution table for one source."""
    return source_species_dir( workflow_root, config ) / source / TREE_COUNTS_ALL_STRUCTURES.format( source = source )


def source_per_structure_path( workflow_root: Path, config: dict, source: str, structure: str ) -> Path:
    """The per-structure deconvolution table for one source + structure."""
    return ( source_species_dir( workflow_root, config ) / source
             / TREE_COUNTS_PER_STRUCTURE_DIR
             / TREE_COUNTS_PER_STRUCTURE.format( source = source, structure = structure ) )


def resolve_sources( workflow_root: Path, config: dict ) -> list:
    """
    Resolve config 'annotation_sources' to a concrete, validated source list.

    "all" -> every subdirectory of <annogroups_dir>/<species_set>/ that carries a
    deconvolution all_structures table. An explicit list -> validated as-is.

    Exits 1 if the species dir is missing, "all" finds nothing, or a named source
    lacks its all_structures table (a typo / unbuilt source must fail loudly).
    """
    species_dir = source_species_dir( workflow_root, config )
    if not species_dir.is_dir():
        print( f"CRITICAL ERROR: annogroups species dir not found: {species_dir}", file = sys.stderr )
        print( "  Verify inputs.annogroups_dir + species_set_name resolve into output_to_input.", file = sys.stderr )
        sys.exit( 1 )

    requested = config.get( "annotation_sources", "all" )
    if isinstance( requested, str ) and requested.strip().lower() == "all":
        sources = sorted(
            entry.name for entry in species_dir.iterdir()
            if entry.is_dir() and source_all_structures_path( workflow_root, config, entry.name ).is_file()
        )
        if not sources:
            print( f"CRITICAL ERROR: annotation_sources is 'all' but no source under {species_dir} "
                   f"exposes a deconvolution all_structures table", file = sys.stderr )
            sys.exit( 1 )
        return sources

    if not isinstance( requested, list ) or not requested:
        print( f"CRITICAL ERROR: annotation_sources must be 'all' or a non-empty list, got: {requested!r}", file = sys.stderr )
        sys.exit( 1 )

    sources = [ str( s ).strip() for s in requested if str( s ).strip() ]
    for source in sources:
        all_structures_path = source_all_structures_path( workflow_root, config, source )
        if not all_structures_path.is_file():
            print( f"CRITICAL ERROR: source '{source}' has no deconvolution all_structures table", file = sys.stderr )
            print( f"  Expected: {all_structures_path}", file = sys.stderr )
            print( "  Verify the source name and that annogroups exposed its 4-output deconvolution.", file = sys.stderr )
            sys.exit( 1 )
    return sources


def read_structure_clade_set( per_structure_path: Path ) -> set:
    """
    The clade_id_names that appear as columns in one per-structure tree-counts
    file (reads the header only). This is how a structure's own clade set — and
    therefore its ambiguous nodes — is determined for the ONE and SOME scopes.

    Exits 1 if the file is missing (a requested structure that was never produced
    must fail loudly, not silently contribute an empty clade set).
    """
    if not per_structure_path.is_file():
        print( f"CRITICAL ERROR: per-structure tree-counts file not found: {per_structure_path}", file = sys.stderr )
        print( "  Verify the structure id exists in the annogroups deconvolution (structure_001..NNN).", file = sys.stderr )
        sys.exit( 1 )
    with open( per_structure_path, 'r' ) as input_per_structure:
        _identity_indices, clades = parse_tree_counts_header( input_per_structure.readline() )
    return { clade[ 'clade_id_name' ] for clade in clades }


def resolve_some_structures( workflow_root: Path, config: dict ) -> list:
    """
    Resolve the SOME scope's structure set: the UNION of the inline
    structure_scopes.some.structure_ids list and the structure ids read from
    structure_scopes.some.selected_structures_file (if given).

    The file may be a bare list (one structure_id per line) OR a TSV carrying a
    Structure_ID column (e.g. a trees_species/BLOCK_user_requests selection).
    Blank lines and '#' comments are ignored.

    Exits 1 if SOME is enabled but resolves to zero structures.
    """
    some_config = config.get( "structure_scopes", {} ).get( "some", {} )
    structure_ids = set()

    for structure_id in ( some_config.get( "structure_ids" ) or [] ):
        structure_id = str( structure_id ).strip()
        if structure_id:
            structure_ids.add( structure_id )

    selected_file = some_config.get( "selected_structures_file" )
    if selected_file and str( selected_file ).strip():
        selected_path = resolve_input_path( workflow_root, str( selected_file ).strip() )
        if not selected_path.is_file():
            print( f"CRITICAL ERROR: selected_structures_file not found: {selected_path}", file = sys.stderr )
            print( "  Set structure_scopes.some.selected_structures_file to a real path or \"\".", file = sys.stderr )
            sys.exit( 1 )
        structure_ids |= _read_structure_ids_from_file( selected_path )

    resolved = sorted( structure_ids )
    if not resolved:
        print( "CRITICAL ERROR: SOME scope is enabled but resolved to zero structures", file = sys.stderr )
        print( "  Provide structure_scopes.some.structure_ids and/or a non-empty selected_structures_file.", file = sys.stderr )
        sys.exit( 1 )
    return resolved


def _read_structure_ids_from_file( selected_path: Path ) -> set:
    """
    Read structure ids from a selection file. Accepts a bare list (one id per
    line) OR a TSV with a Structure_ID column (header detected via build_header_index).
    """
    structure_ids = set()
    with open( selected_path, 'r' ) as input_selected:
        lines = [ line.rstrip( '\n' ) for line in input_selected ]

    data_lines = [ line for line in lines if line.strip() and not line.lstrip().startswith( '#' ) ]
    if not data_lines:
        return structure_ids

    # TSV-with-header form: a Structure_ID column anywhere in the first data line.
    header_ids___indices = build_header_index( data_lines[ 0 ] )
    if "Structure_ID" in header_ids___indices and '\t' in data_lines[ 0 ]:
        index_structure = header_ids___indices[ "Structure_ID" ]
        for line in data_lines[ 1: ]:
            parts = line.split( '\t' )
            if index_structure < len( parts ) and parts[ index_structure ].strip():
                structure_ids.add( parts[ index_structure ].strip() )
        return structure_ids

    # Bare-list form: one structure id per line (first whitespace token).
    for line in data_lines:
        token = line.split()[ 0 ].strip() if line.split() else ""
        if token:
            structure_ids.add( token )
    return structure_ids


_INTEGRATOR_AI = Path( __file__ ).resolve().parents[ 4 ] / "ai"
if str( _INTEGRATOR_AI ) not in sys.path:
    sys.path.insert( 0, str( _INTEGRATOR_AI ) )

import utils_integrator_shared as _SHARED

find_output_pipeline_root = _SHARED.find_output_pipeline_root
resolve_workflow_run_timestamp_suffix = _SHARED.resolve_workflow_run_timestamp_suffix
build_timestamped_filename = _SHARED.build_timestamped_filename
resolve_timestamped_output_path = _SHARED.resolve_timestamped_output_path


def timestamped_output_path( output_dir: Path, stem: str, output_base: Path, extension: str = '.tsv' ) -> Path:
    """Build a timestamped archival path under output_dir using the shared run suffix (§65)."""
    pipeline_root = find_output_pipeline_root( output_base )
    suffix = resolve_workflow_run_timestamp_suffix( pipeline_root )
    return output_dir / build_timestamped_filename( stem, suffix, extension )
