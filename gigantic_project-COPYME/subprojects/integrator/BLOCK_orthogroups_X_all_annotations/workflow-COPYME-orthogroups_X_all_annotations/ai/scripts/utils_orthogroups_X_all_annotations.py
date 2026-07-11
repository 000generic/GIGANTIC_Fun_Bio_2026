# AI: Claude (Cursor) | Opus 4.8 | 2026 July 10 | Purpose: Shared helpers for the orthogroups_X_all_annotations integration scripts
# Human: Eric Edsinger

"""
Shared helpers for the integrator orthogroups_X_all_annotations pipeline.

Provides:
  - load_config / workflow_root_from_output_dir / resolve_input_path : YAML config + path resolution
  - genus_species_from_phyloname / genus_species_from_full_gigantic_id : GIGANTIC ID -> Genus_species
  - build_header_index               : self-documenting-header column lookup
  - DELIM                            : in-column list delimiter (bare comma, §34)
  - NAME_DELIM                       : delimiter for the annotation NAME columns

    NAME_DELIM deviates from §34 (which mandates the comma as the sole in-column
    delimiter) because GO/Pfam/PANTHER human-readable names frequently CONTAIN
    commas (e.g. "positive regulation of transcription, DNA-templated") and a few
    even contain a semicolon (e.g. Pfam PF13720 "Udp N-acetylglucosamine
    O-acyltransferase; Domain 2") or a pipe. Neither comma, semicolon, nor pipe is
    a safe list separator for these names (all three occur across the species70
    pfam/go/panther maps), so NAME_DELIM is the multi-character token ' // ', which
    has ZERO collisions across all feature names in those maps. Comma-joining (or
    semicolon-joining) would silently corrupt the list (a research-integrity
    failure per AI_BEHAVIOR.md). The paired *_Accessions columns remain strictly
    comma-delimited and §34-compliant; the *_Names columns use ' // ' and Script
    002 fail-fast rejects any name that itself contains ' // '.

All scripts in this workflow import this module via:
    sys.path.insert( 0, str( Path( __file__ ).parent ) )
    import utils_orthogroups_X_all_annotations
"""

from datetime import datetime
from pathlib import Path
import yaml

# In-column multi-value delimiter — bare comma per gigantic_conventions §34.
DELIM = ','

# Delimiter for the annotation NAME columns (see module docstring for the
# deliberate §34 deviation). Multi-character ' // ' — chosen because names can
# contain commas, semicolons, AND pipes; ' // ' has zero collisions in the
# species70 pfam/go/panther maps.
NAME_DELIM = ' // '

# Main output table stem (timestamp suffix appended at run time).
OUTPUT_TABLE_STEM = "1_ai-orthogroups_X_all_annotations"

MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)


def filename_timestamp_suffix( when: datetime = None ) -> str:
    """Return a run timestamp suffix like _july11_1606 (month name + day + hhmm)."""
    when = when or datetime.now()
    month = MONTH_NAMES[ when.month - 1 ]
    return f"_{month}{when.day}_{when.hour:02d}{when.minute:02d}"


def build_timestamped_table_filename( table_stem: str, when: datetime = None ) -> str:
    """Build the headline table filename: <stem>_july11_1606.tsv"""
    return f"{table_stem}{filename_timestamp_suffix( when )}.tsv"


def write_output_table_pointer( output_dir: Path, table_filename: str ):
    """Record the timestamped table filename for validation and RUN-workflow.sh."""
    pointer_path = output_dir / "1-output" / "1_ai-output_table_filename.txt"
    pointer_path.write_text( table_filename + '\n' )


def resolve_output_table_path( output_base: Path ) -> Path:
    """
    Locate the Script 001 output table: pointer file first, then newest timestamped
    match, then legacy fixed-name file.
    """
    output_dir = output_base / "1-output"
    pointer_path = output_dir / "1_ai-output_table_filename.txt"
    if pointer_path.is_file():
        table_filename = pointer_path.read_text().strip()
        table_path = output_dir / table_filename
        if table_path.is_file():
            return table_path
    matches = sorted( output_dir.glob( f"{OUTPUT_TABLE_STEM}_*.tsv" ) )
    if matches:
        return matches[ -1 ]
    legacy_path = output_dir / f"{OUTPUT_TABLE_STEM}.tsv"
    return legacy_path


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


def genus_species_from_phyloname( phyloname: str ) -> str:
    """
    Extract Genus_species from a GIGANTIC phyloname.

    Phyloname = Kingdom_Phylum_Class_Order_Family_Genus_species (7+ fields);
    genus + species occupy positions 5.. (0-indexed). Multi-word species
    (e.g. Hoilungia_hongkongensis_H13) are preserved by joining parts[5:].
    Returns the phyloname unchanged if it has fewer than 7 fields so the caller
    can surface the mismatch rather than silently mis-joining.
    """
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) >= 7:
        return '_'.join( parts_phyloname[ 5: ] )
    return phyloname


def genus_species_from_full_gigantic_id( full_id: str ) -> str:
    """
    Genus_species from a full GIGANTIC sequence identifier.

    Format: g_<gene>-t_<rna>-p_<protein>-n_<phyloname>. The phyloname is
    everything after the final '-n_'. Returns None if the marker is absent so
    the caller can fail fast.
    """
    if '-n_' not in full_id:
        return None
    phyloname = full_id.split( '-n_' )[ -1 ]
    return genus_species_from_phyloname( phyloname )


def build_header_index( header_line: str ) -> dict:
    """
    Map self-documenting header IDs to column indices.

    GIGANTIC TSV headers look like 'Annogroup_ID (canonical annogroup ...)';
    the header_ID is the text before ' (' . Returns { header_ID : index }.
    """
    header_ids___indices = {}
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    for index, column in enumerate( parts_header_line ):
        header_id = column.split( ' (' )[ 0 ].strip()
        header_ids___indices[ header_id ] = index
    return header_ids___indices


def structure_number( structure_id: str ) -> str:
    """'structure_031' -> '031'; anything else returned unchanged."""
    if '_' in structure_id:
        return structure_id.rsplit( '_', 1 )[ 1 ]
    return structure_id


# Annogroup source -> output column prefix (pfam/go/panther membership from annogroups subproject).
ANNOGROUP_SOURCE_PREFIXES = {
    "pfam": "Annogroups_Pfam",
    "go": "Annogroups_GO",
    "panther": "Annogroups_PANTHER",
}


def annogroup_prefix_for_source( source: str ) -> str:
    """Map annogroups subproject source name to the four-column output prefix."""
    return ANNOGROUP_SOURCE_PREFIXES.get( source, f"Annogroups_{source.capitalize()}" )


def annogroup_name_from_map_fields( annogroup_type: str, annotation_definitions: str ) -> str:
    """
    Human-readable annogroup name from the annogroup MAP row.

    Uses Annotation_Definitions when present (feature/combination/architecture).
    Absent-type rows use a fixed label because definitions are empty.
    """
    definitions = annotation_definitions.strip()
    if definitions:
        return definitions
    if annogroup_type == "absent":
        return "Absent from genome"
    return annogroup_type
