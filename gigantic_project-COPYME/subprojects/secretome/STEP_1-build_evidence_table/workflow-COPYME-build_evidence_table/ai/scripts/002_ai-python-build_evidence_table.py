#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Pivot the long-format standardized annotation database into one wide per-protein evidence table per species
# Human: Eric Edsinger

"""
002_ai-python-build_evidence_table.py

For ONE species (one phyloname), reads every available `database_<name>/
gigantic_annotations-database_<name>-<phyloname>.tsv` under the annotation
database directory and pivots them into ONE wide per-protein evidence table.

Output: <phyloname>_evidence_table.tsv with:

    Protein-level columns (4):
        Phyloname
        Protein_Identifier
        Sequence_Length             (from proteome FASTA)
        Total_Database_Hits         (sum of hit counts across all dbs)

    Per-database generic columns (4 per db × N dbs):
        <db>_Hit_Count
        <db>_Unique_Annotation_Count
        <db>_Annotation_Identifiers     (comma-delimited unique sorted)
        <db>_Annotation_Details         (comma-delimited unique sorted)

    Specialized parsed columns:
        signalp_fast_Call               (Sec/SPI | Sec/SPII | Tat/SPI | None)
        signalp_fast_Probability        (float; None if no prediction)
        signalp_slow_Call
        signalp_slow_Probability
        deeploc_Localizations           (DeepLoc top-call localization string,
                                         pipe-separated for multi-compartment
                                         calls; from DeepLoc CSV `Localizations`
                                         column — same string the long-format
                                         DB stores)
        deeploc_Signals                 (DeepLoc Signals column: e.g.
                                         'Signal peptide', 'Mitochondrial
                                         transit peptide', 'None')
        deeploc_Membrane_Types          (DeepLoc 'Membrane types' column:
                                         e.g. 'Soluble', 'Transmembrane')
        deeploc_Cytoplasm_Probability               (float; from CSV)
        deeploc_Nucleus_Probability                 (float; from CSV)
        deeploc_Extracellular_Probability           (float; from CSV)
        deeploc_Cell_Membrane_Probability           (float; from CSV)
        deeploc_Mitochondrion_Probability           (float; from CSV)
        deeploc_Plastid_Probability                 (float; from CSV)
        deeploc_Endoplasmic_Reticulum_Probability   (float; from CSV)
        deeploc_Lysosome_Vacuole_Probability        (float; from CSV)
        deeploc_Golgi_Apparatus_Probability         (float; from CSV)
        deeploc_Peroxisome_Probability              (float; from CSV)
        deeploc_Peripheral_Probability              (float; from CSV)
        deeploc_Transmembrane_Probability           (float; from CSV)
        deeploc_Lipid_Anchor_Probability            (float; from CSV)
        deeploc_Soluble_Probability                 (float; from CSV)
        tmbed_TM_Helix_Count
        tmbed_Beta_Barrel_Count
        tmbed_Signal_Peptide_Count

The pivot is LOSSLESS for the long-format DB: every row collapses into
the appropriate per-protein cell. Specialized columns are derived from
parsing the `Annotation_Details` text of the corresponding dbs (parsing
logic is database-specific and documented inline).

The proteome FASTA drives the output row set: one row per protein in the
FASTA. Proteins with zero rows in any long-format DB get None values
across all per-database columns (their existence is still recorded so
downstream filters know about them).

Notes on the input schema (uniform across all 17 dbs, verified 2026-05-25):
    1  Phyloname
    2  Sequence_Identifier  (protein identifier; matches FASTA header word 1)
    3  Domain_Start
    4  Domain_Stop
    5  Database_Name        (e.g. pfam, signalp_fast, deeploc, ...)
    6  Annotation_Identifier
    7  Annotation_Details

DeepLoc limitation: the long-format DB only carries the TOP localization
+ its probability per protein. Other compartments' probabilities (e.g.
Transmembrane, Cell membrane, ER) are NOT in the long-format DB. To get
the full DeepLoc probability vector, downstream consumers must augment by
reading `annotations_hmms/output_to_input/BLOCK_deeploc/*.csv` directly.
"""

import argparse
import csv
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path


# DeepLoc CSV columns and the safe-identifier column suffix used in output TSV
DEEPLOC_PROBABILITY_COLUMNS = [
    ( "Cytoplasm",             "Cytoplasm_Probability" ),
    ( "Nucleus",               "Nucleus_Probability" ),
    ( "Extracellular",         "Extracellular_Probability" ),
    ( "Cell membrane",         "Cell_Membrane_Probability" ),
    ( "Mitochondrion",         "Mitochondrion_Probability" ),
    ( "Plastid",               "Plastid_Probability" ),
    ( "Endoplasmic reticulum", "Endoplasmic_Reticulum_Probability" ),
    ( "Lysosome/Vacuole",      "Lysosome_Vacuole_Probability" ),
    ( "Golgi apparatus",       "Golgi_Apparatus_Probability" ),
    ( "Peroxisome",            "Peroxisome_Probability" ),
    ( "Peripheral",            "Peripheral_Probability" ),
    ( "Transmembrane",         "Transmembrane_Probability" ),
    ( "Lipid anchor",          "Lipid_Anchor_Probability" ),
    ( "Soluble",               "Soluble_Probability" ),
]
DEEPLOC_STRING_COLUMNS = [
    ( "Localizations",   "Localizations" ),
    ( "Signals",         "Signals" ),
    ( "Membrane types",  "Membrane_Types" ),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Pivot long-format standardized annotation database into one wide per-protein evidence table for one species."
    )
    parser.add_argument(
        "--input-fasta",
        required = True,
        help = "Path to the canonical proteome FASTA for this species; drives the output row set.",
    )
    parser.add_argument(
        "--annotation-database-dir",
        required = True,
        help = "Path to the annotation_databases/ directory produced by BLOCK_build_annotation_database (contains database_<name>/ subdirs).",
    )
    parser.add_argument(
        "--output-dir",
        required = True,
        help = "Directory where <phyloname>_evidence_table.tsv + log are written.",
    )
    parser.add_argument(
        "--phyloname",
        required = True,
        help = "GIGANTIC phyloname for the species (used in input/output naming).",
    )
    parser.add_argument(
        "--deeploc-csv-dir",
        required = True,
        help = "Path to the directory of DeepLoc CSV files (annotations_hmms/output_to_input/BLOCK_deeploc/). Used to augment the evidence table with per-compartment probabilities that are NOT preserved in the long-format annotation database.",
    )
    parser.add_argument(
        "--include-databases",
        required = False,
        default = "",
        help = "Comma-separated whitelist of database short names to include in the pivot (e.g. 'pfam,deeploc,metapredict,signalp_fast,signalp_slow,tmbed'). When empty (default), every discovered database is included. Use this to keep the evidence table tight by dropping IPR sub-databases the downstream analysis does not need.",
    )
    return parser.parse_args()


# =============================================================================
# PROTEOME FASTA — drive the output row set
# =============================================================================

def read_proteome_protein_ids_and_lengths( input_fasta_path, logger ):
    """
    Walk the proteome FASTA and return ordered list of
    ( protein_identifier, sequence_length ). Protein identifier is the
    first whitespace-separated token after the leading '>'.
    """
    protein_ids_with_lengths = []
    current_identifier = None
    current_sequence_parts = []

    input_fasta = open( input_fasta_path, "r" )
    for line in input_fasta:
        line = line.rstrip( "\n" )
        if not line:
            continue
        if line.startswith( ">" ):
            if current_identifier is not None:
                sequence_length = sum( len( part ) for part in current_sequence_parts )
                protein_ids_with_lengths.append( ( current_identifier, sequence_length ) )
            current_identifier = line[ 1: ].split()[ 0 ]
            current_sequence_parts = []
        else:
            current_sequence_parts.append( line )
    if current_identifier is not None:
        sequence_length = sum( len( part ) for part in current_sequence_parts )
        protein_ids_with_lengths.append( ( current_identifier, sequence_length ) )
    input_fasta.close()

    logger.info( f"Proteome FASTA: read {len( protein_ids_with_lengths )} proteins" )
    return protein_ids_with_lengths


# =============================================================================
# LONG-FORMAT DB — discover and read
# =============================================================================

def discover_database_files( annotation_database_directory, phyloname, include_set, logger ):
    """
    Discover every database_<name>/gigantic_annotations-database_<name>-<phyloname>.tsv
    under the annotation_database_directory. Returns ordered dict:
        database_name -> path_to_per_species_tsv

    If `include_set` is non-empty, only databases whose short name is in
    that set are included. If empty, every discovered database is included.
    """
    annotation_database_directory = Path( annotation_database_directory )
    if not annotation_database_directory.exists():
        logger.error( f"CRITICAL ERROR: annotation database directory does not exist: {annotation_database_directory}" )
        sys.exit( 1 )

    database_names___paths = {}
    skipped_by_include_filter = []
    for database_subdirectory in sorted( annotation_database_directory.iterdir() ):
        if not database_subdirectory.is_dir():
            continue
        if not database_subdirectory.name.startswith( "database_" ):
            continue
        database_name = database_subdirectory.name[ len( "database_" ): ]
        if include_set and database_name not in include_set:
            skipped_by_include_filter.append( database_name )
            continue
        expected_filename = f"gigantic_annotations-database_{database_name}-{phyloname}.tsv"
        tsv_path = database_subdirectory / expected_filename
        if tsv_path.exists():
            database_names___paths[ database_name ] = tsv_path
        else:
            logger.warning( f"  database {database_name}: no per-species TSV at {tsv_path}" )

    if include_set:
        missing_from_disk = sorted( include_set - set( database_names___paths.keys() ) - set( skipped_by_include_filter ) )
        if missing_from_disk:
            logger.warning( f"  --include-databases names not found on disk for this species: {missing_from_disk}" )
        if skipped_by_include_filter:
            logger.info( f"  Skipped by --include-databases filter ({len( skipped_by_include_filter )}): {sorted( skipped_by_include_filter )}" )

    if not database_names___paths:
        logger.error( f"CRITICAL ERROR: zero per-species TSVs found for phyloname {phyloname} under {annotation_database_directory}" )
        if include_set:
            logger.error( f"  Note: --include-databases filter was active with: {sorted( include_set )}" )
        sys.exit( 1 )

    logger.info( f"Discovered {len( database_names___paths )} database TSVs for {phyloname}: {sorted( database_names___paths )}" )
    return database_names___paths


def read_database_rows_per_protein( database_tsv_path, logger ):
    """
    Read one long-format database TSV and group rows by protein identifier.

    Returns dict:
        protein_identifier -> list of dict( start, stop, accession, details )

    The header is skipped. Required columns (positional):
        col 0 = Phyloname              ( ignored — same for all rows )
        col 1 = Sequence_Identifier
        col 2 = Domain_Start
        col 3 = Domain_Stop
        col 4 = Database_Name          ( ignored — same for all rows )
        col 5 = Annotation_Identifier
        col 6 = Annotation_Details
    """
    protein_ids___annotation_records = defaultdict( list )

    input_tsv = open( database_tsv_path, "r" )
    next( input_tsv )  # discard header
    for line in input_tsv:
        line = line.rstrip( "\n" )
        if not line:
            continue
        parts = line.split( "\t" )
        if len( parts ) < 7:
            logger.warning( f"  malformed row in {database_tsv_path.name}: < 7 cols, skipping: {line[ :120 ]}" )
            continue
        protein_identifier = parts[ 1 ]
        annotation_record = {
            "start":      parts[ 2 ],
            "stop":       parts[ 3 ],
            "accession":  parts[ 5 ],
            "details":    parts[ 6 ],
        }
        protein_ids___annotation_records[ protein_identifier ].append( annotation_record )
    input_tsv.close()
    return protein_ids___annotation_records


# =============================================================================
# DEEPLOC CSV — read raw per-compartment probabilities
# =============================================================================

def read_deeploc_csv( deeploc_csv_path, logger ):
    """
    Read DeepLoc 2.0 native CSV output (one row per protein) and return
        protein_identifier -> dict( <safe_column_name> -> str_value )

    Columns kept:
        DEEPLOC_STRING_COLUMNS:       Localizations, Signals, Membrane types
        DEEPLOC_PROBABILITY_COLUMNS:  Cytoplasm, Nucleus, Extracellular,
                                      Cell membrane, Mitochondrion, Plastid,
                                      Endoplasmic reticulum, Lysosome/Vacuole,
                                      Golgi apparatus, Peroxisome,
                                      Peripheral, Transmembrane, Lipid anchor,
                                      Soluble
    """
    if not deeploc_csv_path.exists():
        logger.error( f"CRITICAL ERROR: DeepLoc CSV not found: {deeploc_csv_path}" )
        sys.exit( 1 )
    protein_ids___deeploc_fields = {}
    with open( deeploc_csv_path, newline = '' ) as f:
        reader = csv.DictReader( f )
        for row in reader:
            protein_identifier = row[ "Protein_ID" ]
            fields = {}
            for csv_col, safe_name in DEEPLOC_STRING_COLUMNS:
                fields[ safe_name ] = row.get( csv_col, "None" ) or "None"
            for csv_col, safe_name in DEEPLOC_PROBABILITY_COLUMNS:
                value = row.get( csv_col, "" )
                fields[ safe_name ] = value if value else "None"
            protein_ids___deeploc_fields[ protein_identifier ] = fields
    logger.info( f"DeepLoc CSV: read {len( protein_ids___deeploc_fields )} proteins from {deeploc_csv_path.name}" )
    return protein_ids___deeploc_fields


# =============================================================================
# SPECIALIZED PARSERS — for 4 dbs with structured details
# =============================================================================

# Matches `probability=0.999746` (the first occurrence in details string)
SIGNALP_PROBABILITY_PATTERN = re.compile( r"probability=([0-9.eE+-]+)" )

def signalp_call_and_probability_from_record( annotation_records ):
    """
    SignalP long-format DB has exactly ONE row per protein.
        Annotation_Identifier = call ( Sec/SPI | Sec/SPII | Tat/SPI | None )
        Annotation_Details    = 'probability=<float>,cleavage_site=...'
                                or 'probability=<float>'         ( None call )
    Returns ( call, probability_string ). probability_string is the raw
    float as a string ( for None / parse failure, returns 'None' ).
    """
    if len( annotation_records ) == 0:
        return ( "None", "None" )
    record = annotation_records[ 0 ]  # SignalP is 1 row per protein
    call = record[ "accession" ]
    details = record[ "details" ]
    match = SIGNALP_PROBABILITY_PATTERN.search( details )
    probability = match.group( 1 ) if match else "None"
    return ( call, probability )


# DeepLoc specialized columns now come from the raw CSV (see read_deeploc_csv)
# rather than from the long-format DB, because the long-format DB only
# preserved the top-localization probability and dropped all other compartment
# probabilities. Reading the CSV directly recovers the full 14-probability
# vector per protein.


def tmbed_region_counts( annotation_records ):
    """
    TMBed long-format DB has 1+ rows per protein, where
        Annotation_Identifier = '<region_type>_<N>' ( e.g. tm_helix_3, beta_barrel_1, signal_peptide_1 )
        Annotation_Details    = '<region type human-readable>'
    Returns ( tm_helix_count, beta_barrel_count, signal_peptide_count ).
    """
    tm_helix_count = 0
    beta_barrel_count = 0
    signal_peptide_count = 0
    for record in annotation_records:
        accession = record[ "accession" ]
        if accession.startswith( "tm_helix_" ):
            tm_helix_count += 1
        elif accession.startswith( "beta_barrel_" ):
            beta_barrel_count += 1
        elif accession.startswith( "signal_peptide_" ):
            signal_peptide_count += 1
        # Any other accession ( e.g. 'unannotated_tmbed-N' ) is ignored for these counts.
    return ( tm_helix_count, beta_barrel_count, signal_peptide_count )


# =============================================================================
# GENERIC SUMMARIZERS — for all 17 dbs
# =============================================================================

def summarize_records( annotation_records ):
    """
    Generic 4-value summary of one protein's annotation_records list for ONE database:
        Hit_Count                   = len( records )
        Unique_Annotation_Count     = number of distinct Annotation_Identifier values
        Annotation_Identifiers      = comma-delimited sorted unique list
        Annotation_Details          = comma-delimited sorted unique list
    """
    hit_count = len( annotation_records )
    if hit_count == 0:
        return ( "0", "0", "None", "None" )
    annotation_identifiers = sorted( { r[ "accession" ] for r in annotation_records } )
    annotation_details_unique = sorted( { r[ "details" ] for r in annotation_records } )
    unique_annotation_count = len( annotation_identifiers )
    return (
        str( hit_count ),
        str( unique_annotation_count ),
        ",".join( annotation_identifiers ),
        ",".join( annotation_details_unique ),
    )


# =============================================================================
# OUTPUT HEADER
# =============================================================================

def build_output_header( database_names_sorted ):
    """
    Construct the wide TSV header. Order:
        Protein-level (4)
        For each database (alphabetical):
            generic 4 cols
            specialized cols for signalp_*, deeploc, tmbed (appended right after that db's generic block)
    """
    header_cells = [
        "Phyloname (GIGANTIC phyloname for the species)",
        "Protein_Identifier (protein identifier from proteome FASTA word 1 of header)",
        "Sequence_Length (residue count from proteome FASTA)",
        "Total_Database_Hits (sum of per-database Hit_Count across all available annotation databases)",
    ]
    for database_name in database_names_sorted:
        header_cells.append( f"{database_name}_Hit_Count (number of rows for this protein in database_{database_name}; 0 if no annotation)" )
        header_cells.append( f"{database_name}_Unique_Annotation_Count (number of distinct Annotation_Identifier values for this protein in database_{database_name})" )
        header_cells.append( f"{database_name}_Annotation_Identifiers (comma delimited sorted unique list of Annotation_Identifier values; None if no annotation)" )
        header_cells.append( f"{database_name}_Annotation_Details (comma delimited sorted unique list of Annotation_Details values; None if no annotation)" )
        if database_name in ( "signalp_fast", "signalp_slow" ):
            header_cells.append( f"{database_name}_Call (parsed from Annotation_Identifier; one of Sec/SPI Sec/SPII Tat/SPI None)" )
            header_cells.append( f"{database_name}_Probability (parsed from Annotation_Details probability=X; float as string or None)" )
        elif database_name == "deeploc":
            # Specialized DeepLoc cols come from the raw DeepLoc CSV (full 14-probability
            # vector) rather than the long-format DB which only kept the top call's probability.
            for _csv_col, safe_name in DEEPLOC_STRING_COLUMNS:
                header_cells.append( f"deeploc_{safe_name} (DeepLoc CSV column '{_csv_col}'; raw string)" )
            for _csv_col, safe_name in DEEPLOC_PROBABILITY_COLUMNS:
                header_cells.append( f"deeploc_{safe_name} (DeepLoc CSV column '{_csv_col}'; float probability as string or None)" )
        elif database_name == "tmbed":
            header_cells.append( "tmbed_TM_Helix_Count (count of tm_helix_N Annotation_Identifier rows for this protein)" )
            header_cells.append( "tmbed_Beta_Barrel_Count (count of beta_barrel_N Annotation_Identifier rows for this protein)" )
            header_cells.append( "tmbed_Signal_Peptide_Count (count of signal_peptide_N Annotation_Identifier rows for this protein)" )
    return "\t".join( header_cells ) + "\n"


def build_output_row( phyloname, protein_identifier, sequence_length, database_names_sorted, db_to_records, deeploc_csv_records ):
    """
    Construct one wide TSV row for one protein. Mirrors build_output_header order.
    deeploc_csv_records: dict protein_id -> dict of DeepLoc CSV fields (safe names).
    """
    cells = [
        phyloname,
        protein_identifier,
        str( sequence_length ),
        "PLACEHOLDER_TOTAL",  # filled in after per-db loop
    ]
    total_hits = 0
    for database_name in database_names_sorted:
        annotation_records = db_to_records.get( database_name, {} ).get( protein_identifier, [] )
        hit_count_string, unique_count_string, identifiers_string, details_string = summarize_records( annotation_records )
        total_hits += int( hit_count_string )
        cells.append( hit_count_string )
        cells.append( unique_count_string )
        cells.append( identifiers_string )
        cells.append( details_string )
        if database_name in ( "signalp_fast", "signalp_slow" ):
            call, probability = signalp_call_and_probability_from_record( annotation_records )
            cells.append( call )
            cells.append( probability )
        elif database_name == "deeploc":
            deeploc_record = deeploc_csv_records.get( protein_identifier, {} )
            for _csv_col, safe_name in DEEPLOC_STRING_COLUMNS:
                cells.append( deeploc_record.get( safe_name, "None" ) )
            for _csv_col, safe_name in DEEPLOC_PROBABILITY_COLUMNS:
                cells.append( deeploc_record.get( safe_name, "None" ) )
        elif database_name == "tmbed":
            tm_helix_count, beta_barrel_count, signal_peptide_count = tmbed_region_counts( annotation_records )
            cells.append( str( tm_helix_count ) )
            cells.append( str( beta_barrel_count ) )
            cells.append( str( signal_peptide_count ) )
    cells[ 3 ] = str( total_hits )
    return "\t".join( cells ) + "\n"


# =============================================================================
# MAIN
# =============================================================================

def main():
    args = parse_args()

    output_directory = Path( args.output_dir ).resolve()
    output_directory.mkdir( parents = True, exist_ok = True )

    log_path = output_directory / f"2_ai-log-build_evidence_table_{args.phyloname}.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [
            logging.FileHandler( log_path ),
            logging.StreamHandler( sys.stdout ),
        ],
    )
    logger = logging.getLogger( __name__ )

    evidence_table_path = output_directory / f"{args.phyloname}_evidence_table.tsv"

    logger.info( "=" * 70 )
    logger.info( "Script 002: Build per-protein evidence table (one species)" )
    logger.info( "=" * 70 )
    include_set = set( s.strip() for s in args.include_databases.split( "," ) if s.strip() )

    logger.info( f"Phyloname:                  {args.phyloname}" )
    logger.info( f"Input FASTA:                {args.input_fasta}" )
    logger.info( f"Annotation database dir:    {args.annotation_database_dir}" )
    logger.info( f"DeepLoc CSV dir:            {args.deeploc_csv_dir}" )
    logger.info( f"Include databases filter:   {sorted( include_set ) if include_set else '(none — include everything discovered)'}" )
    logger.info( f"Output dir:                 {output_directory}" )

    # --- Proteome FASTA: drives row set --------------------------------------
    protein_ids_with_lengths = read_proteome_protein_ids_and_lengths(
        Path( args.input_fasta ), logger,
    )
    if len( protein_ids_with_lengths ) == 0:
        logger.error( f"CRITICAL ERROR: proteome FASTA contained 0 proteins: {args.input_fasta}" )
        sys.exit( 1 )
    protein_id_set = set( pid for ( pid, _ ) in protein_ids_with_lengths )

    # --- Discover available database TSVs ------------------------------------
    database_names___paths = discover_database_files(
        args.annotation_database_dir, args.phyloname, include_set, logger,
    )

    # --- Read each database into protein_id -> records dict ------------------
    # Some annotation TSVs may contain protein IDs not present in the canonical
    # proteome FASTA — typically EvidentialGene multi-locus concatenated IDs
    # whose filename forms exceed 253 chars and were filtered out by upstream
    # tool BLOCKs (signalp / tmbed) but accidentally retained in DB parsers
    # operating on raw IPR/DeepLoc/MetaPredict outputs. We log + skip such
    # orphan IDs rather than fail; they cannot appear in output rows anyway
    # because the proteome FASTA drives row generation.
    db_to_records = {}
    db_to_orphan_count = {}
    for database_name in sorted( database_names___paths ):
        tsv_path = database_names___paths[ database_name ]
        logger.info( f"Reading database_{database_name}: {tsv_path.name}" )
        protein_ids___records = read_database_rows_per_protein( tsv_path, logger )
        foreign_ids = [ pid for pid in protein_ids___records.keys() if pid not in protein_id_set ]
        orphan_count = len( foreign_ids )
        if orphan_count > 0:
            logger.warning( f"  database_{database_name}: {orphan_count} protein IDs not in proteome FASTA — skipping (likely upstream-filtered EvidentialGene multi-locus IDs)" )
            for orphan_id in foreign_ids:
                del protein_ids___records[ orphan_id ]
        db_to_records[ database_name ] = protein_ids___records
        db_to_orphan_count[ database_name ] = orphan_count
        logger.info( f"  database_{database_name}: {sum( len( v ) for v in protein_ids___records.values() )} rows across {len( protein_ids___records )} proteins (after skipping {orphan_count} orphan IDs)" )

    # --- Read DeepLoc CSV for per-compartment probabilities ------------------
    deeploc_csv_path = Path( args.deeploc_csv_dir ) / f"{args.phyloname}_deeploc_predictions.csv"
    deeploc_csv_records = read_deeploc_csv( deeploc_csv_path, logger )
    deeploc_foreign_ids = [ pid for pid in deeploc_csv_records.keys() if pid not in protein_id_set ]
    if len( deeploc_foreign_ids ) > 0:
        logger.warning( f"  DeepLoc CSV: {len( deeploc_foreign_ids )} protein IDs not in proteome FASTA — skipping (likely upstream-filtered EvidentialGene multi-locus IDs)" )
        for orphan_id in deeploc_foreign_ids:
            del deeploc_csv_records[ orphan_id ]

    # --- Write wide TSV ------------------------------------------------------
    database_names_sorted = sorted( db_to_records.keys() )
    output_evidence_table = open( evidence_table_path, "w" )
    output_evidence_table.write( build_output_header( database_names_sorted ) )

    proteins_with_any_annotation = 0
    for ( protein_identifier, sequence_length ) in protein_ids_with_lengths:
        row = build_output_row(
            args.phyloname,
            protein_identifier,
            sequence_length,
            database_names_sorted,
            db_to_records,
            deeploc_csv_records,
        )
        output_evidence_table.write( row )
        # row's 4th tab-delimited cell is Total_Database_Hits ( int )
        if int( row.split( "\t" )[ 3 ] ) > 0:
            proteins_with_any_annotation += 1
    output_evidence_table.close()

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Proteins in FASTA:                          {len( protein_ids_with_lengths ):,}" )
    logger.info( f"Proteins with >= 1 database hit:            {proteins_with_any_annotation:,}" )
    logger.info( f"Proteins with 0 database hits:              {len( protein_ids_with_lengths ) - proteins_with_any_annotation:,}" )
    logger.info( f"Databases pivoted:                          {len( database_names_sorted )}" )
    logger.info( f"Output columns: 4 + {len( database_names_sorted )} * 4 + specialized" )
    total_orphans = sum( db_to_orphan_count.values() )
    if total_orphans > 0:
        logger.info( f"Orphan annotation rows skipped (IDs not in FASTA): {total_orphans}" )
        for db_name, n in sorted( db_to_orphan_count.items() ):
            if n > 0:
                logger.info( f"    database_{db_name}: {n}" )
    logger.info( f"Output evidence table: {evidence_table_path}" )


if __name__ == "__main__":
    main()
