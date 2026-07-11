#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Add BLASTP top 10 hits (IDs + e-values + headers) per protein
# Human: Eric Edsinger

"""
006_ai-python-augment_with_blastp_top10.py

Per species, append BLASTP top-10 columns to the per-species evidence table:

  BLASTP_Top_10_Hit_IDs                  (comma list of top 10 NCBI nr hit IDs)
  BLASTP_Top_10_Hit_E_Values             (comma list of e-values, matched 1:1 to IDs)
  BLASTP_Top_10_Hit_Headers              (comma list of hit description strings)

Source: `one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/<phyloname>_top_hits.tsv`.
That TSV ( regenerated 2026-05-25 with the new e-values column from the
upstream patch — commit 56e423f ) has one row per query protein.

If a protein from the input TSV has no row in the top_hits TSV
( e.g., diamond returned zero hits for it ), all three new columns are 'None'.
"""

import argparse
import csv
import logging
import sys
from pathlib import Path


def resolve_against_workflow_root( raw_path, workflow_root ):
    """Resolve an upstream input path so it survives NextFlow work/ execution.

    Config-derived paths (BLASTP top-hits dir) are relative to the workflow
    directory. NextFlow runs each task in a work/ subdir, so a bare relative
    path would resolve against the wrong CWD. Anchor relative paths against
    workflow_root (absolute, passed by main.nf as ${projectDir}/..); leave
    already-absolute paths and staged NextFlow inputs untouched.
    """
    path = Path( raw_path )
    if path.is_absolute():
        return path
    return ( Path( workflow_root ) / path ).resolve()


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Append BLASTP top-10 hit IDs + e-values + headers as 3 new columns."
    )
    parser.add_argument( "--workflow-root", required = True,
                         help = "Absolute path to the workflow directory (main.nf passes ${projectDir}/..); relative --blastp-top-hits-tsv is resolved against this." )
    parser.add_argument( "--input-tsv", required = True,
                         help = "Per-species TSV input ( previous augment stage )." )
    parser.add_argument( "--blastp-top-hits-tsv", required = True,
                         help = "Per-species top_hits.tsv from one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/." )
    parser.add_argument( "--run-label", required = True )
    parser.add_argument( "--phyloname", required = True )
    parser.add_argument( "--output-dir", required = True )
    return parser.parse_args()


def load_blastp_top_hits( top_hits_tsv_path, logger ):
    """
    Return dict protein_id → ( top_10_ids_str, top_10_evalues_str, top_10_headers_str )
    where the str values are already comma-delimited ( as stored in the source TSV ).
    """
    lookup = {}
    if not Path( top_hits_tsv_path ).exists():
        logger.warning( f"top_hits TSV not found: {top_hits_tsv_path} — every protein gets None for BLASTP columns" )
        return lookup

    with open( top_hits_tsv_path, newline = "" ) as f:
        reader = csv.DictReader( f, delimiter = "\t" )
        # Find columns by short Header_ID prefix (col headers are self-documenting).
        short_to_full = { fn.split( " " )[ 0 ]: fn for fn in reader.fieldnames }
        for required in ( "Query_Sequence_ID", "Top_10_Hit_IDs", "Top_10_Hit_E_Values", "Top_10_Hit_Headers" ):
            if required not in short_to_full:
                logger.error( f"CRITICAL: required column '{required}' missing from {top_hits_tsv_path}" )
                logger.error( f"  available short names: {sorted( short_to_full )}" )
                sys.exit( 1 )
        for row in reader:
            qid     = row[ short_to_full[ "Query_Sequence_ID" ] ]
            ids     = row[ short_to_full[ "Top_10_Hit_IDs" ] ]
            evalues = row[ short_to_full[ "Top_10_Hit_E_Values" ] ]
            headers = row[ short_to_full[ "Top_10_Hit_Headers" ] ]
            lookup[ qid ] = ( ids or "None", evalues or "None", headers or "None" )
    logger.info( f"BLASTP top_hits loaded: {len( lookup ):,} proteins with hits" )
    return lookup


def find_protein_id_column( fieldnames ):
    for fn in fieldnames:
        if fn.split( " " )[ 0 ] == "Protein_Identifier":
            return fn
    raise KeyError( "no 'Protein_Identifier' column found in input TSV header" )


def main():
    args = parse_args()
    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    # Resolve config-derived BLASTP top-hits path against the workflow root so
    # the relative config path survives NextFlow's work/ execution dirs.
    input_blastp_top_hits_tsv = resolve_against_workflow_root( args.blastp_top_hits_tsv, args.workflow_root )

    log_path = output_dir / f"{args.phyloname}_{args.run_label}_log-augment_blastp.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [ logging.FileHandler( log_path ), logging.StreamHandler( sys.stdout ) ],
    )
    logger = logging.getLogger( __name__ )

    logger.info( "=" * 70 )
    logger.info( "Script 006: augment_with_blastp_top10" )
    logger.info( "=" * 70 )
    logger.info( f"Run label:       {args.run_label}" )
    logger.info( f"Phyloname:       {args.phyloname}" )
    logger.info( f"Workflow root:   {args.workflow_root}" )
    logger.info( f"Input TSV:       {args.input_tsv}" )
    logger.info( f"top_hits TSV:    {input_blastp_top_hits_tsv}" )

    blastp_lookup = load_blastp_top_hits( input_blastp_top_hits_tsv, logger )

    out_path = output_dir / f"{args.phyloname}_{args.run_label}_blastp_augmented.tsv"

    new_columns = [
        "BLASTP_Top_10_Hit_IDs (comma delimited list of top 10 NCBI nr hit sequence IDs from DIAMOND BLASTp; None if protein had zero diamond hits)",
        "BLASTP_Top_10_Hit_E_Values (comma delimited list of top 10 DIAMOND BLASTp e-values matched 1:1 with BLASTP_Top_10_Hit_IDs; None if no hits)",
        "BLASTP_Top_10_Hit_Headers (comma delimited list of top 10 NCBI nr hit description strings matched 1:1 with BLASTP_Top_10_Hit_IDs; None if no hits)",
    ]

    n_in = 0
    n_with_hits = 0
    with open( args.input_tsv, newline = "" ) as fin, open( out_path, "w", newline = "" ) as fout:
        reader = csv.DictReader( fin, delimiter = "\t" )
        protein_id_col = find_protein_id_column( reader.fieldnames )
        out_fieldnames = list( reader.fieldnames ) + new_columns
        writer = csv.DictWriter( fout, fieldnames = out_fieldnames, delimiter = "\t" )
        writer.writeheader()

        for row in reader:
            n_in += 1
            protein_id = row[ protein_id_col ]
            hit = blastp_lookup.get( protein_id )
            if hit is None:
                row[ new_columns[ 0 ] ] = "None"
                row[ new_columns[ 1 ] ] = "None"
                row[ new_columns[ 2 ] ] = "None"
            else:
                row[ new_columns[ 0 ] ] = hit[ 0 ]
                row[ new_columns[ 1 ] ] = hit[ 1 ]
                row[ new_columns[ 2 ] ] = hit[ 2 ]
                n_with_hits += 1
            writer.writerow( row )

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Proteins read:               {n_in:,}" )
    logger.info( f"Proteins with BLASTP hits:   {n_with_hits:,}  ({100 * n_with_hits / n_in:.2f}%)" if n_in else "n=0" )
    logger.info( f"Output: {out_path}" )


if __name__ == "__main__":
    main()
