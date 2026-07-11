# AI: Cursor | Opus 4.8 | 2026 July 11 08:40 | Purpose: Show orthogroup distribution of every Wnt annotation signature (Pfam/PANTHER/InterPro) to prove the 'many orthogroups' effect is signature-independent
# Human: Eric Edsinger
"""
Leonid recalls the term as 'Wnt ligand' and is unsure whether it is Pfam, GO, or
PANTHER. There is no signature literally named 'Wnt ligand', but the Wnt ligand
family is captured by several signatures. This script computes, for the NEW OrthoHMM
run, the per-orthogroup distribution of each Wnt signature so we can confirm the
conclusion (one dominant orthogroup + a few incidental/multidomain members) does not
depend on which database's Wnt term is used.

Signatures checked (all identify Wnt ligand proteins):
    Pfam      PF00110      'wnt family'
    PANTHER   PTHR12027    'WNT RELATED'
    SMART     SM00097      'wnt1_3'
    PRINTS    PR01349      'Wnt protein signature'
    InterPro  IPR005817    'Wnt'   (consolidated entry; union of all member signatures)
"""

from pathlib import Path
from collections import defaultdict

workspace_root = Path( "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/subprojects" )
input_raw_dir = workspace_root / "annotations_hmms/output_to_input/BLOCK_interproscan"
input_spine = workspace_root / "orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv"

# target signatures: label -> (column_index_for_accession, accession_value)
# raw InterProScan columns (0-indexed): 0 protein, 3 analysis, 4 signature_acc, 5 sig_desc, 11 ipr_acc, 12 ipr_desc
signatures = {
    "Pfam PF00110 'wnt family'":        ( 4, "PF00110" ),
    "PANTHER PTHR12027 'WNT RELATED'":  ( 4, "PTHR12027" ),
    "SMART SM00097 'wnt1_3'":           ( 4, "SM00097" ),
    "PRINTS PR01349 'Wnt protein sig'": ( 4, "PR01349" ),
    "InterPro IPR005817 'Wnt'":         ( 11, "IPR005817" ),
}

# ---- build sequence -> orthogroup + orthogroup sizes ----
sequences___orthogroups = {}
orthogroups___member_counts = {}
with open( input_spine, "r" ) as input_spine_file:
    for line in input_spine_file:
        line = line.rstrip( "\n" )
        parts = line.split( "\t" )
        og_id = parts[ 0 ]
        members = parts[ 1: ]
        orthogroups___member_counts[ og_id ] = len( members )
        for member in members:
            sequences___orthogroups[ member ] = og_id

# ---- one pass over raw interproscan collecting sequences per signature ----
signature_labels___sequences = { label: set() for label in signatures }
raw_files = sorted( input_raw_dir.glob( "*_interproscan_results.tsv" ) )
for raw_file in raw_files:
    with open( raw_file, "r" ) as input_raw:
        for line in input_raw:
            line = line.rstrip( "\n" )
            parts = line.split( "\t" )
            if len( parts ) < 13:
                continue
            sequence_id = parts[ 0 ]
            for label, ( column_index, accession_value ) in signatures.items():
                if parts[ column_index ] == accession_value:
                    signature_labels___sequences[ label ].add( sequence_id )

# ---- summarize distribution per signature ----
print( f"{'Signature':40s} {'#seqs':>6} {'#OGs':>5} {'dominant_OG':>12} {'dom_seqs':>9} {'scattered':>10}" )
print( "-" * 90 )
for label in signatures:
    sequences = signature_labels___sequences[ label ]
    orthogroups___counts = defaultdict( int )
    for sequence_id in sequences:
        og_id = sequences___orthogroups.get( sequence_id )
        if og_id is not None:
            orthogroups___counts[ og_id ] += 1
    if orthogroups___counts:
        dominant_og, dominant_count = max( orthogroups___counts.items(), key=lambda x: x[ 1 ] )
        scattered = len( sequences ) - dominant_count
    else:
        dominant_og, dominant_count, scattered = "NONE", 0, 0
    print( f"{label:40s} {len( sequences ):6d} {len( orthogroups___counts ):5d} {dominant_og:>12} {dominant_count:9d} {scattered:10d}" )
