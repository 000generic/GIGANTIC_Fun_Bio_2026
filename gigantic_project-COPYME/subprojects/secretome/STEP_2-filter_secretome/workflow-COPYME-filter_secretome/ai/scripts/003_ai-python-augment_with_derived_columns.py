#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Add derived columns (cysteine count, pfam max copies per accession) to filtered secretome TSV
# Human: Eric Edsinger

"""
003_ai-python-augment_with_derived_columns.py

Append derived columns to the per-species filtered secretome TSV:

  Cysteine_Count                            int  ( count of literal 'C' in proteome FASTA sequence )
  Cysteine_Percent                          float as string  ( 100 * Cysteine_Count / Sequence_Length )
  Pfam_Max_Hits_Per_Single_Accession        int  ( max # of pfam hits any single accession had for this protein )

The cysteine count comes from a single pass over the proteome FASTA. The
pfam max-per-accession comes from the long-format database_pfam TSV — the
STEP_1 evidence table only keeps unique pfam accessions, dropping the
per-accession hit counts needed for Leonid's "drop if >4 of the same" rule.

Both inputs are species-scoped, so this script runs per species and only
opens the files relevant to its phyloname.
"""

import argparse
import csv
import logging
import sys
from collections import Counter
from pathlib import Path


def resolve_against_workflow_root( raw_path, workflow_root ):
    """Resolve an upstream input path so it survives NextFlow work/ execution.

    Config-derived paths (proteome FASTA dir, annotation database dir) are
    relative to the workflow directory. NextFlow runs each task in a work/
    subdir, so a bare relative path would resolve against the wrong CWD. Anchor
    relative paths against workflow_root (absolute, passed by main.nf as
    ${projectDir}/..); leave already-absolute paths and staged NextFlow inputs
    untouched.
    """
    path = Path( raw_path )
    if path.is_absolute():
        return path
    return ( Path( workflow_root ) / path ).resolve()


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Append cysteine count + pfam max-per-accession columns to filtered secretome TSV."
    )
    parser.add_argument( "--workflow-root", required = True,
                         help = "Absolute path to the workflow directory (main.nf passes ${projectDir}/..); relative --proteome-fasta and --pfam-long-format-tsv are resolved against this." )
    parser.add_argument( "--filtered-tsv", required = True,
                         help = "Per-species filtered TSV from script 002." )
    parser.add_argument( "--proteome-fasta", required = True,
                         help = "Canonical species70 proteome FASTA." )
    parser.add_argument( "--pfam-long-format-tsv", required = True,
                         help = "database_pfam per-species TSV from BLOCK_build_annotation_database (one row per pfam hit)." )
    parser.add_argument( "--run-label", required = True )
    parser.add_argument( "--phyloname", required = True )
    parser.add_argument( "--output-dir", required = True )
    return parser.parse_args()


def read_proteome_cysteine_counts( fasta_path, logger ):
    """Return dict protein_id -> ( cysteine_count, sequence_length )."""
    counts = {}
    current_id = None
    current_seq_parts = []
    with open( fasta_path ) as f:
        for line in f:
            line = line.rstrip( "\n" )
            if not line:
                continue
            if line.startswith( ">" ):
                if current_id is not None:
                    seq = "".join( current_seq_parts )
                    counts[ current_id ] = ( seq.count( "C" ), len( seq ) )
                current_id = line[ 1: ].split()[ 0 ]
                current_seq_parts = []
            else:
                current_seq_parts.append( line )
        if current_id is not None:
            seq = "".join( current_seq_parts )
            counts[ current_id ] = ( seq.count( "C" ), len( seq ) )
    logger.info( f"Proteome FASTA: {len( counts ):,} proteins; cysteine counts computed" )
    return counts


def read_pfam_max_hits_per_accession( pfam_tsv_path, logger ):
    """
    For each protein, return max # of hits any single pfam accession had.

    Long-format DB schema ( 7 cols, same for every database_<name> TSV ):
      0  Phyloname
      1  Sequence_Identifier
      2  Domain_Start
      3  Domain_Stop
      4  Database_Name
      5  Annotation_Identifier   ← pfam accession ( e.g. PF00001 )
      6  Annotation_Details
    """
    if not Path( pfam_tsv_path ).exists():
        logger.warning( f"pfam long-format TSV not found: {pfam_tsv_path} — every protein gets Pfam_Max_Hits_Per_Single_Accession = 0" )
        return {}

    protein_accession_counts = {}   # protein_id -> Counter( accession -> count )
    with open( pfam_tsv_path ) as f:
        header = next( f, None )    # discard header
        for line in f:
            line = line.rstrip( "\n" )
            if not line:
                continue
            parts = line.split( "\t" )
            if len( parts ) < 7:
                continue
            protein_id = parts[ 1 ]
            accession = parts[ 5 ]
            if protein_id not in protein_accession_counts:
                protein_accession_counts[ protein_id ] = Counter()
            protein_accession_counts[ protein_id ][ accession ] += 1

    max_per_protein = {
        protein_id: max( counts.values() ) if counts else 0
        for protein_id, counts in protein_accession_counts.items()
    }
    logger.info( f"pfam long-format TSV: {len( protein_accession_counts ):,} proteins with pfam hits" )
    return max_per_protein


def find_protein_id_column( fieldnames ):
    """The STEP_1 evidence table uses 'Protein_Identifier (...)'. Return the full column name."""
    for fn in fieldnames:
        if fn.split( " " )[ 0 ] == "Protein_Identifier":
            return fn
    raise KeyError( "no 'Protein_Identifier' column found in filtered TSV header" )


def main():
    args = parse_args()
    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    # Resolve config-derived upstream paths against the workflow root so relative
    # config paths survive NextFlow's work/ execution dirs.
    input_proteome_fasta = resolve_against_workflow_root( args.proteome_fasta, args.workflow_root )
    input_pfam_long_format_tsv = resolve_against_workflow_root( args.pfam_long_format_tsv, args.workflow_root )

    log_path = output_dir / f"{args.phyloname}_{args.run_label}_log-augment_derived.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [ logging.FileHandler( log_path ), logging.StreamHandler( sys.stdout ) ],
    )
    logger = logging.getLogger( __name__ )

    logger.info( "=" * 70 )
    logger.info( "Script 003: augment_with_derived_columns" )
    logger.info( "=" * 70 )
    logger.info( f"Run label:       {args.run_label}" )
    logger.info( f"Phyloname:       {args.phyloname}" )
    logger.info( f"Workflow root:   {args.workflow_root}" )
    logger.info( f"Filtered TSV:    {args.filtered_tsv}" )
    logger.info( f"Proteome FASTA:  {input_proteome_fasta}" )
    logger.info( f"Pfam long-fmt:   {input_pfam_long_format_tsv}" )

    cys_lookup = read_proteome_cysteine_counts( input_proteome_fasta, logger )
    pfam_max_lookup = read_pfam_max_hits_per_accession( input_pfam_long_format_tsv, logger )

    out_path = output_dir / f"{args.phyloname}_{args.run_label}_secretome.tsv"

    n_kept = 0
    with open( args.filtered_tsv, newline = "" ) as fin, open( out_path, "w", newline = "" ) as fout:
        reader = csv.DictReader( fin, delimiter = "\t" )
        protein_id_col = find_protein_id_column( reader.fieldnames )

        new_columns = [
            "Cysteine_Count (count of C residues in proteome FASTA sequence; passthrough column, no filter)",
            "Cysteine_Percent (100 * Cysteine_Count / Sequence_Length; passthrough column, no filter)",
            "Pfam_Max_Hits_Per_Single_Accession (max # of pfam hits any single accession had for this protein; used for the >4-of-same drop rule)",
        ]
        out_fieldnames = list( reader.fieldnames ) + new_columns
        writer = csv.DictWriter( fout, fieldnames = out_fieldnames, delimiter = "\t" )
        writer.writeheader()

        for row in reader:
            protein_id = row[ protein_id_col ]
            cys_count, seq_len = cys_lookup.get( protein_id, ( None, None ) )
            if cys_count is None:
                row[ new_columns[ 0 ] ] = "None"
                row[ new_columns[ 1 ] ] = "None"
            else:
                row[ new_columns[ 0 ] ] = str( cys_count )
                row[ new_columns[ 1 ] ] = f"{( 100 * cys_count / seq_len ):.3f}" if seq_len else "None"
            row[ new_columns[ 2 ] ] = str( pfam_max_lookup.get( protein_id, 0 ) )
            writer.writerow( row )
            n_kept += 1

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Proteins in input ( = output ):  {n_kept:,}" )
    logger.info( f"Output:                          {out_path}" )


if __name__ == "__main__":
    main()
