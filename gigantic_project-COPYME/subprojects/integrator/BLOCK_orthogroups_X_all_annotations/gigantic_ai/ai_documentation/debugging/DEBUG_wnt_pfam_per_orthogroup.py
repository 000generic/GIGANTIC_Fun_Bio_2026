# AI: Cursor | Opus 4.8 | 2026 July 11 08:00 | Purpose: Investigate distribution of Pfam PF00110 (wnt family) across OrthoHMM orthogroups in the new 202k run
# Human: Eric Edsinger
"""
Diagnostic: count how many PF00110 ('wnt family' = Wnt ligand) sequences fall into
each orthogroup in the NEW OrthoHMM run, using the raw per-sequence Pfam annotations
and the orthogroup membership spine. This is independent of the aggregated integrator
table (which only shows the UNION of domains per orthogroup).

Outputs a small report: per-orthogroup PF00110 sequence count, orthogroup total
member count, and the fraction of the orthogroup that is Wnt-annotated. Also lists
any PF00110 sequences not found in any orthogroup.
"""

from pathlib import Path
import sys

pfam_target = "PF00110"

# Resolve paths relative to workspace root
workspace_root = Path( "/blue/moroz/share/edsinger/projects/ai_ctenophores/github-gigantic_1/GIGANTIC/gigantic_project-COPYME/subprojects" )
input_pfam_dir = workspace_root / "annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam"

# Spine (orthogroup membership) can be overridden on the command line so we can
# compare the new GIGANTIC run against the older BLOCK_orthohmm runs.
default_spine = workspace_root / "orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv"
if len( sys.argv ) > 1:
    input_spine = Path( sys.argv[ 1 ] )
else:
    input_spine = default_spine
print( f"SPINE: {input_spine}" )

# ---- Step 1: collect all sequences carrying PF00110 ----
# Protein_Identifier	MD5	Sequence_Length	Analysis_Database	Accession	Description	...
wnt_sequences = set()
pfam_files = sorted( input_pfam_dir.glob( "pfam-*.tsv" ) )
if not pfam_files:
    print( f"CRITICAL: no pfam files found in {input_pfam_dir}" )
    sys.exit( 1 )

for pfam_file in pfam_files:
    with open( pfam_file, "r" ) as input_pfam:
        header = input_pfam.readline()
        for line in input_pfam:
            line = line.rstrip( "\n" )
            parts = line.split( "\t" )
            if len( parts ) < 5:
                continue
            sequence_id = parts[ 0 ]
            accession = parts[ 4 ]
            if accession == pfam_target:
                wnt_sequences.add( sequence_id )

print( f"PF00110-carrying sequences (across all 70 species): {len( wnt_sequences )}" )

# ---- Step 2: map each member sequence to its orthogroup ----
# OG000000	member1	member2	...
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

print( f"Total orthogroups: {len( orthogroups___member_counts )}" )
print( f"Total member sequences in spine: {len( sequences___orthogroups )}" )

# ---- Step 3: count PF00110 sequences per orthogroup ----
orthogroups___wnt_counts = {}
wnt_not_in_any_orthogroup = []
for sequence_id in wnt_sequences:
    og_id = sequences___orthogroups.get( sequence_id )
    if og_id is None:
        wnt_not_in_any_orthogroup.append( sequence_id )
        continue
    orthogroups___wnt_counts[ og_id ] = orthogroups___wnt_counts.get( og_id, 0 ) + 1

print( "" )
print( f"Orthogroups containing >=1 PF00110 sequence: {len( orthogroups___wnt_counts )}" )
print( f"PF00110 sequences not found in any orthogroup: {len( wnt_not_in_any_orthogroup )}" )
if wnt_not_in_any_orthogroup:
    for sequence_id in sorted( wnt_not_in_any_orthogroup )[ :20 ]:
        print( f"    ABSENT: len={len( sequence_id )}  {sequence_id}" )

print( "" )
print( "Per-orthogroup PF00110 distribution (sorted by wnt count desc):" )
print( "OG_ID\tWnt_Seq_Count\tOG_Member_Count\tWnt_Fraction_Percent" )
total_wnt_placed = 0
for og_id, wnt_count in sorted( orthogroups___wnt_counts.items(), key=lambda x: x[ 1 ], reverse=True ):
    member_count = orthogroups___member_counts[ og_id ]
    fraction = 100.0 * wnt_count / member_count
    total_wnt_placed += wnt_count
    print( f"{og_id}\t{wnt_count}\t{member_count}\t{fraction:.1f}" )

print( "" )
print( f"Total PF00110 sequences placed into orthogroups: {total_wnt_placed}" )
