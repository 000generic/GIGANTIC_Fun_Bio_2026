# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Shared helpers for the species_X_all_annotations integration scripts
# Human: Eric Edsinger

"""
Shared helpers for the integrator species_X_all_annotations pipeline.

This BLOCK builds a per-species proteome table: one row per protein sequence,
with every per-gene annotation GIGANTIC produces joined onto it. The spine is
the genomesDB STEP_4 per-species sequence table (sequence id + amino acid
sequence). Most sources join on the full GIGANTIC protein identifier; two
(gene_sizes, hotspots) join on the bare g_ gene field within a species.

Provides:
  - load_config / workflow_root_from_output_dir / resolve_input_path : YAML + paths
  - parse_full_gigantic_id           : split a GIGANTIC sequence ID into parts
  - genus_species_from_phyloname     : phyloname -> Genus_species
  - phyloname_from_spine_filename    : sequence-table filename -> phyloname
  - build_header_index               : self-documenting-header column lookup
  - format_top_nr_hits               : top-N nr DIAMOND hits -> one cell
  - split_go_identifier_source       : 'GO:NNNNNNN(InterPro)' -> ( source, clean_id )
  - DELIM / SUBDELIM / NA            : in-column delimiters + missing-value token

All scripts in this workflow import this module via:
    sys.path.insert( 0, str( Path( __file__ ).parent ) )
    import utils_species_X_all_annotations as U
"""

from datetime import datetime
from pathlib import Path
import sys
import yaml

# In-column delimiters.
#   DELIM    (bare comma, per gigantic_conventions §34) separates simple values
#            whose tokens never contain a comma (IDs, counts, GO terms).
#   SUBDELIM (semicolon) separates composite entries whose text MAY contain
#            commas (nr hit headers, Pfam/PANTHER descriptions, phylogenetic
#            paths). The annogroups subproject already uses ';' for its
#            'definition ==accession' pairs, so this matches existing precedent.
DELIM = ','
SUBDELIM = ';'

# Missing-value token. Sources cover different species / are run at different
# times; a value absent for a given protein is recorded NA, never silently
# dropped (per AI_BEHAVIOR.md zero-tolerance for silent artifacts).
NA = 'NA'

# Delimiter for annotation NAME columns (see orthogroups utils — names may contain commas).
NAME_DELIM = ' // '

VALIDATION_REPORT_STEM = "3_ai-validation_report"

MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)

# Annogroup source -> four-column output prefix.
ANNOGROUP_SOURCE_PREFIXES = {
    "pfam": "Annogroups_Pfam",
    "go": "Annogroups_GO",
    "panther": "Annogroups_PANTHER",
}


def filename_timestamp_suffix( when: datetime = None ) -> str:
    """Return a run timestamp suffix like _july11_1647 (month name + day + hhmm)."""
    when = when or datetime.now()
    month = MONTH_NAMES[ when.month - 1 ]
    return f"_{month}{when.day}_{when.hour:02d}{when.minute:02d}"


def build_timestamped_proteome_base_filename( phyloname: str, when: datetime = None ) -> str:
    """Build per-species base table filename with run timestamp."""
    return f"{phyloname}-proteome_annotations-base{filename_timestamp_suffix( when )}.tsv"


def build_timestamped_proteome_wide_filename( phyloname: str, when: datetime = None ) -> str:
    """Build per-species wide table filename with run timestamp."""
    return f"{phyloname}-proteome_all_annotations{filename_timestamp_suffix( when )}.tsv"


def build_timestamped_availability_summary_filename( when: datetime = None ) -> str:
    """Build feature availability summary filename with run timestamp."""
    return f"feature_availability_summary{filename_timestamp_suffix( when )}.tsv"


def build_timestamped_validation_report_filename( timestamp_suffix: str ) -> str:
    """Build validation report filename: 3_ai-validation_report_july11_1647.txt"""
    return f"{VALIDATION_REPORT_STEM}{timestamp_suffix}.txt"


def write_run_timestamp_pointer( shared_output_dir: Path, timestamp_suffix: str ):
    """Record the run timestamp suffix for Scripts 002 and 003."""
    pointer_path = shared_output_dir / "1_ai-run_timestamp_suffix.txt"
    pointer_path.write_text( timestamp_suffix + '\n' )


def resolve_run_timestamp_suffix( shared_output_dir: Path ) -> str:
    """
    Read the run timestamp suffix written by Script 001. Fail-fast if missing
    when timestamped base tables exist but the pointer does not.
    """
    pointer_path = shared_output_dir / "1_ai-run_timestamp_suffix.txt"
    if pointer_path.is_file():
        return pointer_path.read_text().strip()
    matches = list( shared_output_dir.glob( "*-proteome_annotations-base_*.tsv" ) )
    if matches:
        newest = max( matches, key = lambda path: path.stat().st_mtime )
        marker = "-proteome_annotations-base"
        base = newest.name[ :-4 ] if newest.name.endswith( '.tsv' ) else newest.name
        if marker in base:
            return base.split( marker, 1 )[ 1 ]
    return filename_timestamp_suffix()


def annogroup_prefix_for_source( source: str ) -> str:
    """Map annogroups subproject source name to the four-column output prefix."""
    return ANNOGROUP_SOURCE_PREFIXES.get( source, f"Annogroups_{source.capitalize()}" )


def annogroup_name_from_map_fields( annogroup_type: str, annotation_definitions: str ) -> str:
    """Human-readable annogroup name from the annogroup MAP row."""
    definitions = annotation_definitions.strip()
    if definitions:
        return definitions
    if annogroup_type == "absent":
        return "Absent from genome"
    return annogroup_type


def guard_name( label: str, identifier: str, name: str ):
    """Fail-fast if a name would corrupt the NAME_DELIM-separated list."""
    if NAME_DELIM in name:
        print(
            f"CRITICAL ERROR: {label} name for {identifier} contains NAME_DELIM "
            f"{NAME_DELIM!r} and would corrupt the *_Names list: {name!r}",
            file = sys.stderr,
        )
        sys.exit( 1 )


def format_per_protein_annotation_columns(
    identifiers: list,
    names: list = None,
    source_available: bool = True,
    names_blank: bool = False,
) -> list:
    """
    Build the four per-protein annotation columns for one row.

    Species_Count is 1 when this protein carries at least one annotation of the
    type (one species, one protein). Sequence_Count is the non-redundant count
    of annotation identifiers on this protein. When the source is unavailable
    for the species, all four cells are NA.
    """
    if not source_available:
        return [ NA, NA, NA, NA ]
    if not identifiers:
        return [ '0', '0', '', '' ]
    species_count = '1'
    sequence_count = str( len( identifiers ) )
    identifiers_cell = DELIM.join( identifiers )
    if names_blank:
        names_cell = ''
    elif names is not None:
        names_cell = NAME_DELIM.join( names )
    else:
        names_cell = NAME_DELIM.join( identifiers )
    return [ species_count, sequence_count, identifiers_cell, names_cell ]


def feature_header_columns( prefix: str, label: str, names_blank: bool = False ) -> list:
    """Self-documenting headers for one annotation type's four columns."""
    if names_blank:
        names_desc = (
            f"{prefix}_Names (intentionally blank; {label} has no separate human-readable name -- "
            f"see {prefix}_Identifiers)"
        )
    else:
        names_desc = (
            f"{prefix}_Names (' // ' delimited {label} names aligned to {prefix}_Identifiers; "
            f"' // ' used because names may contain commas, semicolons, or pipes)"
        )
    return [
        f"{prefix}_Species_Count (1 if this protein carries at least one {label} annotation else 0; NA if source unavailable for species)",
        f"{prefix}_Sequence_Count (non-redundant count of {label} identifiers on this protein; NA if source unavailable for species)",
        f"{prefix}_Identifiers (comma delimited non-redundant {label} identifiers on this protein)",
        names_desc,
    ]


def load_config( config_path: str ) -> dict:
    """Load the START_HERE-user_config.yaml into a nested dict."""
    with open( config_path, 'r' ) as input_config:
        config = yaml.safe_load( input_config )
    return config


def workflow_root_from_output_dir( output_dir: str ) -> Path:
    """
    The workflow root is the parent of OUTPUT_pipeline. Input paths in the
    YAML are written relative to the workflow root (per gigantic_conventions §5).
    """
    return Path( output_dir ).resolve().parent


def resolve_input_path( workflow_root: Path, relative_path: str ) -> Path:
    """Resolve a YAML-relative input path against the workflow root."""
    return ( workflow_root / relative_path ).resolve()


def parse_full_gigantic_id( full_id: str ) -> tuple:
    """
    Split a full GIGANTIC sequence identifier into ( source_gene_field,
    phyloname, genus_species ).

    Format: g_<gene>-t_<rna>-p_<protein>-n_<phyloname>
    Delimiters '-t_', '-p_', '-n_' are hyphen-prefixed; phylonames and gene
    fields use underscores (no hyphens), so the splits are unambiguous.

    Returns ( None, None, None ) if the ID does not contain the expected
    markers (caller decides how to handle).
    """
    if '-n_' not in full_id or not full_id.startswith( 'g_' ):
        return ( None, None, None )

    # g_ field: between leading 'g_' and the first '-t_'
    source_gene_field = full_id.split( '-t_' )[ 0 ][ 2: ]

    # phyloname: everything after the final '-n_'
    phyloname = full_id.split( '-n_' )[ -1 ]

    genus_species = genus_species_from_phyloname( phyloname )

    return ( source_gene_field, phyloname, genus_species )


def genus_species_from_phyloname( phyloname: str ) -> str:
    """
    Extract Genus_species from a GIGANTIC phyloname.

    Phyloname = Kingdom_Phylum_Class_Order_Family_Genus_species (7+ fields);
    genus + species occupy positions 5.. (0-indexed). Multi-word species
    (e.g. Hoilungia_hongkongensis_H13) are preserved by joining parts[5:].
    """
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) >= 7:
        return '_'.join( parts_phyloname[ 5: ] )
    # Fallback: phyloname is non-standard; return as-is so the caller can
    # surface the mismatch rather than silently mis-joining.
    return phyloname


def phyloname_from_spine_filename( filename: str ) -> str:
    """
    Derive the phyloname from a genomesDB STEP_4 sequence-table filename.

    Pattern: <phyloname>-T1-proteome-sequence_table.tsv
    """
    marker = '-T1-proteome-sequence_table.tsv'
    if filename.endswith( marker ):
        return filename[ :-len( marker ) ]
    return filename


def build_header_index( header_line: str ) -> dict:
    """
    Map self-documenting header IDs to column indices.

    GIGANTIC TSV headers look like 'Status (DARK if all three axes False ...)';
    the header_ID is the text before ' (' . Returns { header_ID : index }.
    """
    header_ids___indices = {}
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    for index, column in enumerate( parts_header_line ):
        header_id = column.split( ' (' )[ 0 ].strip()
        header_ids___indices[ header_id ] = index
    return header_ids___indices


def split_go_identifier_source( annotation_identifier: str ) -> tuple:
    """
    Split an annotations_hmms GO Annotation_Identifier into ( source, clean_id ).

    The consolidated GO table tags each GO term with the tool that produced it,
    as a parenthetical suffix: 'GO:0005737(PANTHER)' / 'GO:0042732(InterPro)'.
    Returns ( 'PANTHER' | 'InterPro' | None, 'GO:NNNNNNN' ).
    """
    if annotation_identifier.endswith( '(PANTHER)' ):
        return ( 'PANTHER', annotation_identifier[ :-len( '(PANTHER)' ) ] )
    if annotation_identifier.endswith( '(InterPro)' ):
        return ( 'InterPro', annotation_identifier[ :-len( '(InterPro)' ) ] )
    return ( None, annotation_identifier )


def _slice_nr_header( headers_text: str, hit_ids: list, index: int ) -> str:
    """
    Recover hit `index`'s full header text from the comma-joined Top_N_Hit_Headers
    string. The header descriptions themselves contain commas, so a naive split
    is ambiguous; instead slice between consecutive hit accessions (which never
    contain commas and appear in order at the start of each header entry).
    """
    accession = hit_ids[ index ]
    start = headers_text.find( accession )
    if start == -1:
        return ''
    if index + 1 < len( hit_ids ):
        next_position = headers_text.find( hit_ids[ index + 1 ], start + len( accession ) )
        end = next_position if next_position != -1 else len( headers_text )
    else:
        end = len( headers_text )
    segment = headers_text[ start:end ].strip().rstrip( ',' ).strip()
    return segment


def format_top_nr_hits( hit_ids_cell: str, hit_headers_cell: str, hit_evalues_cell: str, top_n: int ) -> str:
    """
    Build the Top_N_NR_Hits cell from the one_direction_homologs parallel fields
    Top_10_Hit_IDs / Top_10_Hit_Headers / Top_10_Hit_E_Values.

    Hit accessions and e-values are clean comma lists; hit headers may contain
    commas (so they are recovered by accession-boundary slicing). The result is
    SUBDELIM (';') separated, each entry: '<hit header text> (e-value <e>)'.
    Returns NA when there are no hits.
    """
    hit_ids = [ token.strip() for token in hit_ids_cell.split( ',' ) if token.strip() ]
    hit_evalues = [ token.strip() for token in hit_evalues_cell.split( ',' ) if token.strip() ]
    if not hit_ids:
        return NA

    entries = []
    for index in range( min( top_n, len( hit_ids ) ) ):
        header_segment = _slice_nr_header( hit_headers_cell, hit_ids, index )
        if not header_segment:
            header_segment = hit_ids[ index ]
        evalue = hit_evalues[ index ] if index < len( hit_evalues ) else NA
        entries.append( f"{header_segment} (e-value {evalue})" )
    return SUBDELIM.join( entries ) if entries else NA
