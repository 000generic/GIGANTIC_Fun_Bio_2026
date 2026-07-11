#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Add orthogroup ID + model-species ortholog columns to per-species evidence table
# Human: Eric Edsinger

"""
005_ai-python-augment_with_orthogroups.py

Append orthogroup-membership columns to the per-species evidence table:

  Orthogroup_ID                                       (e.g. OG000007 or 'None')
  Orthogroup_Total_Members                            (int; 0 if protein is not in any OG)
  Orthogroup_Homo_sapiens_Members                     (comma list; or 'None')
  Orthogroup_Drosophila_melanogaster_Members          (comma list; or 'None')
  Orthogroup_Caenorhabditis_elegans_Members           (comma list; or 'None')
  Orthogroup_Aplysia_californica_Members              (comma list; or 'None')

Source: `orthogroups/output_to_input/BLOCK_orthohmm/orthogroups_gigantic_ids.tsv`.
That file has one row per orthogroup; col 0 is the OG identifier, cols 1..N
are tab-delimited GIGANTIC protein IDs (each ends with `-n_<phyloname>`).

This script runs PER species. It loads the full orthogroups TSV once, builds
a reverse index ( protein_id → og_id ) and per-OG member dictionaries for the
4 model species, then walks the input TSV and appends 6 columns.

For Leonid's spec: 'sequence identifier, human, fly, worm, aplysia identifiers
- total number of sequences in the orthogroup'.
"""

import argparse
import csv
import logging
import sys
from collections import defaultdict
from pathlib import Path


MODEL_SPECIES_PHYLONAME_SUFFIXES = [
    ( "Homo_sapiens",             "-n_Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens" ),
    ( "Drosophila_melanogaster",  "-n_Metazoa_Arthropoda_Insecta_Diptera_Drosophilidae_Drosophila_melanogaster" ),
    ( "Caenorhabditis_elegans",   "-n_Metazoa_Nematoda_Chromadorea_Rhabditida_Rhabditidae_Caenorhabditis_elegans" ),
    ( "Aplysia_californica",      "-n_Metazoa_Mollusca_Gastropoda_Aplysiida_Aplysiidae_Aplysia_californica" ),
]


def resolve_against_workflow_root( raw_path, workflow_root ):
    """Resolve an upstream input path so it survives NextFlow work/ execution.

    Config-derived paths (orthogroups TSV) are relative to the workflow
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
        description = "Append orthogroup membership + 4 model-species ortholog columns to per-species TSV."
    )
    parser.add_argument( "--workflow-root", required = True,
                         help = "Absolute path to the workflow directory (main.nf passes ${projectDir}/..); relative --orthogroups-tsv is resolved against this." )
    parser.add_argument( "--input-tsv", required = True,
                         help = "Per-species TSV input ( previous augment stage output )." )
    parser.add_argument( "--orthogroups-tsv", required = True,
                         help = "orthogroups_gigantic_ids.tsv from orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/." )
    parser.add_argument( "--run-label", required = True )
    parser.add_argument( "--phyloname", required = True )
    parser.add_argument( "--output-dir", required = True )
    return parser.parse_args()


def load_orthogroups( og_tsv_path, logger ):
    """
    Read orthogroups_gigantic_ids.tsv. Return:
      protein_to_og:  dict protein_id → og_id
      og_total_count: dict og_id → int total member count
      og_model_members: dict og_id → dict( model_species_name → [member_protein_ids] )

    File format: each line is `OG_ID<TAB>protein_id_1<TAB>protein_id_2<TAB>...`.
    """
    protein_to_og = {}
    og_total_count = {}
    og_model_members = {}

    n_orthogroups = 0
    with open( og_tsv_path ) as f:
        for line in f:
            line = line.rstrip( "\n" )
            if not line:
                continue
            parts = line.split( "\t" )
            og_id = parts[ 0 ]
            members = parts[ 1: ]
            n_orthogroups += 1
            og_total_count[ og_id ] = len( members )
            og_model_members[ og_id ] = { name: [] for name, _ in MODEL_SPECIES_PHYLONAME_SUFFIXES }
            for protein_id in members:
                protein_to_og[ protein_id ] = og_id
                for model_name, suffix in MODEL_SPECIES_PHYLONAME_SUFFIXES:
                    if protein_id.endswith( suffix ):
                        og_model_members[ og_id ][ model_name ].append( protein_id )
                        break
    logger.info( f"Orthogroups loaded: {n_orthogroups:,} OGs, {len( protein_to_og ):,} indexed proteins" )
    return protein_to_og, og_total_count, og_model_members


def find_protein_id_column( fieldnames ):
    for fn in fieldnames:
        if fn.split( " " )[ 0 ] == "Protein_Identifier":
            return fn
    raise KeyError( "no 'Protein_Identifier' column found in input TSV header" )


def main():
    args = parse_args()
    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    # Resolve config-derived orthogroups path against the workflow root so the
    # relative config path survives NextFlow's work/ execution dirs.
    input_orthogroups_tsv = resolve_against_workflow_root( args.orthogroups_tsv, args.workflow_root )

    log_path = output_dir / f"{args.phyloname}_{args.run_label}_log-augment_orthogroups.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [ logging.FileHandler( log_path ), logging.StreamHandler( sys.stdout ) ],
    )
    logger = logging.getLogger( __name__ )

    logger.info( "=" * 70 )
    logger.info( "Script 005: augment_with_orthogroups" )
    logger.info( "=" * 70 )
    logger.info( f"Run label:       {args.run_label}" )
    logger.info( f"Phyloname:       {args.phyloname}" )
    logger.info( f"Workflow root:   {args.workflow_root}" )
    logger.info( f"Input TSV:       {args.input_tsv}" )
    logger.info( f"Orthogroups:     {input_orthogroups_tsv}" )

    protein_to_og, og_total_count, og_model_members = load_orthogroups(
        input_orthogroups_tsv, logger,
    )

    out_path = output_dir / f"{args.phyloname}_{args.run_label}_orthogroups_augmented.tsv"

    new_columns = [
        "Orthogroup_ID (OrthoHMM-assigned orthogroup identifier; None if protein not in any orthogroup)",
        "Orthogroup_Total_Members (total number of protein sequences in the orthogroup across all species; 0 if not in any orthogroup)",
    ]
    for model_name, _ in MODEL_SPECIES_PHYLONAME_SUFFIXES:
        new_columns.append(
            f"Orthogroup_{model_name}_Members (comma delimited list of {model_name} protein identifiers in the same orthogroup; None if none)"
        )

    n_in = 0
    n_with_og = 0
    with open( args.input_tsv, newline = "" ) as fin, open( out_path, "w", newline = "" ) as fout:
        reader = csv.DictReader( fin, delimiter = "\t" )
        protein_id_col = find_protein_id_column( reader.fieldnames )
        out_fieldnames = list( reader.fieldnames ) + new_columns
        writer = csv.DictWriter( fout, fieldnames = out_fieldnames, delimiter = "\t" )
        writer.writeheader()

        for row in reader:
            n_in += 1
            protein_id = row[ protein_id_col ]
            og_id = protein_to_og.get( protein_id )
            if og_id is None:
                row[ new_columns[ 0 ] ] = "None"
                row[ new_columns[ 1 ] ] = "0"
                for i, ( model_name, _ ) in enumerate( MODEL_SPECIES_PHYLONAME_SUFFIXES ):
                    row[ new_columns[ 2 + i ] ] = "None"
            else:
                n_with_og += 1
                row[ new_columns[ 0 ] ] = og_id
                row[ new_columns[ 1 ] ] = str( og_total_count[ og_id ] )
                for i, ( model_name, _ ) in enumerate( MODEL_SPECIES_PHYLONAME_SUFFIXES ):
                    members = og_model_members[ og_id ][ model_name ]
                    row[ new_columns[ 2 + i ] ] = ",".join( members ) if members else "None"
            writer.writerow( row )

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Proteins read:                {n_in:,}" )
    logger.info( f"Proteins with an orthogroup:  {n_with_og:,}  ({100 * n_with_og / n_in:.2f}%)" if n_in else "n=0" )
    logger.info( f"Output: {out_path}" )


if __name__ == "__main__":
    main()
