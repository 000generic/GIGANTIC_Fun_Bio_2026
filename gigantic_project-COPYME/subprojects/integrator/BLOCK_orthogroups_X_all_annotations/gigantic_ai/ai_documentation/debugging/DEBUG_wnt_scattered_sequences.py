# AI: Cursor | Opus 4.8 | 2026 July 11 08:20 | Purpose: Characterize the PF00110 (wnt family) sequences that land OUTSIDE the dominant Wnt orthogroup in the new run
# Human: Eric Edsinger
"""
For the NEW OrthoHMM run, identify every PF00110-carrying sequence that is NOT in the
dominant Wnt orthogroup, and print diagnostic detail so we can tell whether these are
weak/spurious Pfam hits or large multidomain / fusion proteins that legitimately
cluster with a different family:

    - species (phyloname tail)
    - full sequence length
    - PF00110 match span (start-end) and the fraction of the protein it covers
    - PF00110 score/e-value
    - all other Pfam domains on the same sequence
    - the orthogroup it belongs to, that orthogroup's size, and that orthogroup's
      most common Pfam domain (its 'identity')
"""

from pathlib import Path
from collections import defaultdict
import sys

pfam_target = "PF00110"
dominant_orthogroup = "OG000226"

workspace_root = Path( "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/subprojects" )
input_pfam_dir = workspace_root / "annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam"
input_spine = workspace_root / "orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv"

# ---- sequence -> orthogroup, and orthogroup -> members ----
sequences___orthogroups = {}
orthogroups___members = {}
with open( input_spine, "r" ) as input_spine_file:
    for line in input_spine_file:
        line = line.rstrip( "\n" )
        parts = line.split( "\t" )
        og_id = parts[ 0 ]
        members = parts[ 1: ]
        orthogroups___members[ og_id ] = members
        for member in members:
            sequences___orthogroups[ member ] = og_id

# ---- read all pfam annotations, keep per-sequence domain records ----
# Protein_Identifier	MD5	Sequence_Length	Analysis_Database	Accession	Description	Match_Start	Match_End	Score_Or_Evalue	...
sequences___domain_records = defaultdict( list )   # seq_id -> list of (accession, description, start, end, length, score)
wnt_sequences = set()
for pfam_file in sorted( input_pfam_dir.glob( "pfam-*.tsv" ) ):
    with open( pfam_file, "r" ) as input_pfam:
        input_pfam.readline()
        for line in input_pfam:
            line = line.rstrip( "\n" )
            parts = line.split( "\t" )
            if len( parts ) < 9:
                continue
            sequence_id = parts[ 0 ]
            length = parts[ 2 ]
            accession = parts[ 4 ]
            description = parts[ 5 ]
            match_start = parts[ 6 ]
            match_end = parts[ 7 ]
            score = parts[ 8 ]
            sequences___domain_records[ sequence_id ].append(
                ( accession, description, match_start, match_end, length, score ) )
            if accession == pfam_target:
                wnt_sequences.add( sequence_id )

# ---- helper: dominant Pfam of an orthogroup (by number of member sequences carrying it) ----
def dominant_pfam_of_orthogroup( og_id ):
    domain___sequence_count = defaultdict( int )
    for member in orthogroups___members.get( og_id, [] ):
        seen = set()
        for record in sequences___domain_records.get( member, [] ):
            accession, description = record[ 0 ], record[ 1 ]
            if accession not in seen:
                seen.add( accession )
                domain___sequence_count[ ( accession, description ) ] += 1
    if not domain___sequence_count:
        return ( "NONE", "no pfam", 0 )
    ( accession, description ), count = max( domain___sequence_count.items(), key=lambda x: x[ 1 ] )
    return ( accession, description, count )

# ---- report scattered Wnt sequences ----
print( f"Total PF00110 sequences: {len( wnt_sequences )}" )
scattered = []
for sequence_id in wnt_sequences:
    og_id = sequences___orthogroups.get( sequence_id )
    if og_id != dominant_orthogroup:
        scattered.append( sequence_id )
print( f"In dominant {dominant_orthogroup}: {len( wnt_sequences ) - len( scattered )}" )
print( f"Scattered elsewhere: {len( scattered )}" )
print( "" )

for sequence_id in sorted( scattered ):
    og_id = sequences___orthogroups.get( sequence_id )
    og_size = len( orthogroups___members.get( og_id, [] ) )
    dom_acc, dom_desc, dom_count = dominant_pfam_of_orthogroup( og_id )
    # this sequence's PF00110 record(s) + other domains
    wnt_records = [ r for r in sequences___domain_records[ sequence_id ] if r[ 0 ] == pfam_target ]
    other_domains = sorted( set( f"{r[0]}({r[1]})" for r in sequences___domain_records[ sequence_id ] if r[ 0 ] != pfam_target ) )
    seq_length = wnt_records[ 0 ][ 4 ] if wnt_records else "?"
    species = sequence_id.split( "-n_" )[ -1 ]
    print( "=" * 100 )
    print( f"SEQ: {sequence_id}" )
    print( f"  species          : {species}" )
    print( f"  protein length   : {seq_length} aa" )
    print( f"  in orthogroup    : {og_id}  (size {og_size}; dominant Pfam {dom_acc} '{dom_desc}' in {dom_count} members)" )
    for ( acc, desc, start, end, length, score ) in wnt_records:
        try:
            span = int( end ) - int( start ) + 1
            coverage = 100.0 * span / int( length )
            cov_str = f"{coverage:.0f}% of protein"
        except ValueError:
            cov_str = "?"
        print( f"  PF00110 match    : residues {start}-{end} ({cov_str}); score/evalue {score}" )
    print( f"  other Pfam domains ({len( other_domains )}): {', '.join( other_domains ) if other_domains else '(none)'}" )
