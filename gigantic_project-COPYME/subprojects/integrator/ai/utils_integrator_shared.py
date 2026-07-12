# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Shared join keys, delimiters, and gene-group helpers for integrator BLOCKs and aligned subprojects
# Human: Eric Edsinger

"""
Single source of truth for integrator-wide join keys and delimiter constants.

See integrator/ai/integrator_join_and_delimiter_contract.md
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
import yaml

DELIM = ','
SUBDELIM = ';'
NAME_DELIM = ' // '
NA = 'NA'

MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)

# Matches integrator catalog suffix _july11_1645 before the file extension.
TIMESTAMP_SUFFIX_PATTERN = re.compile(
    r'_(?:january|february|march|april|may|june|july|august|september|october|november|december)'
    r'\d{1,2}_\d{4}$',
    re.IGNORECASE,
)

RUN_TIMESTAMP_POINTER_FILENAME = "1_ai-run_timestamp_suffix.txt"

GENE_GROUP_NAME_FALLBACKS = {
    "snap_family": "Synaptosomal-Associated Proteins",
}

DEFAULT_GENE_GROUPS_HGNC_METADATA = (
    "../../../trees_gene_groups/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/"
    "workflow-RUN_1-hgnc_gene_groups/OUTPUT_pipeline/2-output/2_ai-gene_group_metadata.tsv"
)


def load_config( config_path: str ) -> dict:
    with open( config_path, 'r' ) as input_config:
        return yaml.safe_load( input_config )


def workflow_root_from_output_dir( output_dir: str ) -> Path:
    return Path( output_dir ).resolve().parent


def resolve_input_path( workflow_root: Path, relative_path: str ) -> Path:
    return ( workflow_root / relative_path ).resolve()


def genus_species_from_phyloname( phyloname: str ) -> str:
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) >= 7:
        return '_'.join( parts_phyloname[ 5: ] )
    return phyloname


def parse_full_gigantic_id( full_id: str ) -> tuple:
    if '-n_' not in full_id or not full_id.startswith( 'g_' ):
        return ( None, None, None )
    source_gene_field = full_id.split( '-t_' )[ 0 ][ 2: ]
    phyloname = full_id.split( '-n_' )[ -1 ]
    genus_species = genus_species_from_phyloname( phyloname )
    return ( source_gene_field, phyloname, genus_species )


def genus_species_from_full_gigantic_id( full_id: str ) -> str | None:
    if '-n_' not in full_id:
        return None
    return genus_species_from_phyloname( full_id.split( '-n_' )[ -1 ] )


def build_header_index( header_line: str ) -> dict:
    header_ids___indices = {}
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    for index, column in enumerate( parts_header_line ):
        header_id = column.split( ' (' )[ 0 ].strip()
        header_ids___indices[ header_id ] = index
    return header_ids___indices


def guard_name( label: str, identifier: str, name: str ):
    if NAME_DELIM in name:
        print(
            f"CRITICAL ERROR: {label} name for {identifier} contains NAME_DELIM "
            f"{NAME_DELIM!r} and would corrupt the *_Names list: {name!r}",
            file = sys.stderr,
        )
        sys.exit( 1 )


def annogroup_name_from_map_fields( annogroup_type: str, annotation_definitions: str ) -> str:
    definitions = annotation_definitions.strip()
    if definitions:
        return definitions
    if annogroup_type == "absent":
        return "Absent from genome"
    return annogroup_type


def load_gene_group_metadata( metadata_path: Path ) -> dict:
    sanitized___id_name = {}
    if not metadata_path.is_file():
        print(
            f"[shared] WARNING: gene_groups HGNC metadata not found ({metadata_path}); "
            f"gene group ids will fall back to sanitized directory names"
        )
        return sanitized___id_name
    with open( metadata_path, 'r' ) as input_metadata:
        header_ids___indices = build_header_index( input_metadata.readline() )
        index_id = header_ids___indices[ "Gene_Group_ID" ]
        index_name = header_ids___indices[ "Gene_Group_Name" ]
        index_sanitized = header_ids___indices[ "Sanitized_Name" ]
        for line in input_metadata:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sanitized___id_name[ parts[ index_sanitized ] ] = ( parts[ index_id ], parts[ index_name ] )
    return sanitized___id_name


def resolve_gene_group_id_name( sanitized: str, sanitized___id_name: dict ) -> tuple:
    if sanitized in sanitized___id_name:
        return sanitized___id_name[ sanitized ]
    gene_group_id = sanitized
    gene_group_name = GENE_GROUP_NAME_FALLBACKS.get( sanitized, sanitized )
    return ( gene_group_id, gene_group_name )


def sanitized_name_from_ags_path( ags_file: Path ) -> str | None:
    for part in ags_file.parts:
        if part.startswith( "gene_group-" ):
            return part[ len( "gene_group-" ): ]
    return None


# ============================================================================
# Dual-layer output timestamps (GIGANTIC v2.0 pilot — §65)
# ============================================================================


def filename_timestamp_suffix( when: datetime = None ) -> str:
    """Return a run timestamp suffix like _july11_1645 (month name + day + hhmm)."""
    when = when or datetime.now()
    month = MONTH_NAMES[ when.month - 1 ]
    return f"_{month}{when.day}_{when.hour:02d}{when.minute:02d}"


def stable_symlink_basename( filename: str ) -> str:
    """
    Strip a runtime _monthday_hhmm suffix before the extension for output_to_input
    stable symlink names (§65). Returns filename unchanged when no suffix matches.
    """
    if '.' not in filename:
        return filename
    stem, extension = filename.rsplit( '.', 1 )
    if TIMESTAMP_SUFFIX_PATTERN.search( stem ):
        stem = TIMESTAMP_SUFFIX_PATTERN.sub( '', stem )
    return f"{stem}.{extension}"


def build_timestamped_filename( stem: str, suffix: str = None, extension: str = '.tsv' ) -> str:
    """Build <stem>_july11_1645.tsv from stem + suffix (suffix generated when omitted)."""
    suffix = suffix if suffix is not None else filename_timestamp_suffix()
    return f"{stem}{suffix}{extension}"


def find_output_pipeline_root( path: Path ) -> Path:
    """Walk parents until OUTPUT_pipeline is found; else return path's parent."""
    resolved = path.resolve()
    if resolved.name == 'OUTPUT_pipeline':
        return resolved
    for parent in resolved.parents:
        if parent.name == 'OUTPUT_pipeline':
            return parent
    return resolved.parent


def write_workflow_run_timestamp_pointer( output_pipeline_dir: Path, suffix: str = None ):
    """Write 1_ai-run_timestamp_suffix.txt at OUTPUT_pipeline root (RUN-workflow.sh or Script 001)."""
    output_pipeline_dir = Path( output_pipeline_dir )
    output_pipeline_dir.mkdir( parents = True, exist_ok = True )
    suffix = suffix if suffix is not None else filename_timestamp_suffix()
    pointer_path = output_pipeline_dir / RUN_TIMESTAMP_POINTER_FILENAME
    pointer_path.write_text( suffix + '\n' )
    return suffix


def resolve_workflow_run_timestamp_suffix( output_pipeline_dir: Path ) -> str:
    """
    Read the run suffix from OUTPUT_pipeline/1_ai-run_timestamp_suffix.txt.
    Fail-fast when the pointer is missing (workflows must set it before parallel steps).
    """
    output_pipeline_dir = Path( output_pipeline_dir )
    pointer_path = output_pipeline_dir / RUN_TIMESTAMP_POINTER_FILENAME
    if pointer_path.is_file():
        suffix = pointer_path.read_text().strip()
        if suffix:
            return suffix
    print(
        f"CRITICAL ERROR: missing or empty run timestamp pointer: {pointer_path}\n"
        f"RUN-workflow.sh must call write_workflow_run_timestamp.py before NextFlow starts.",
        file = sys.stderr,
    )
    sys.exit( 1 )


def resolve_timestamped_output_path( output_dir: Path, stem: str, output_pipeline_dir: Path = None, extension: str = '.tsv' ) -> Path:
    """Resolve a timestamped output file under output_dir from stem + shared run suffix."""
    pipeline_root = output_pipeline_dir if output_pipeline_dir is not None else find_output_pipeline_root( output_dir )
    suffix = resolve_workflow_run_timestamp_suffix( pipeline_root )
    return output_dir / build_timestamped_filename( stem, suffix, extension )
