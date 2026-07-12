# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Write OUTPUT_pipeline run timestamp pointer before NextFlow starts (§65 dual-layer)
# Human: Eric Edsinger

"""
Write OUTPUT_pipeline/1_ai-run_timestamp_suffix.txt so every parallel script in a
workflow run shares one runtime suffix for timestamped archival filenames.

Called from RUN-workflow.sh immediately before nextflow run.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator_shared as U


def main():
    parser = argparse.ArgumentParser( description = "Write the workflow run timestamp pointer" )
    parser.add_argument( '--output-pipeline', required = True, help = "Path to OUTPUT_pipeline directory" )
    args = parser.parse_args()

    output_pipeline_dir = Path( args.output_pipeline )
    suffix = U.write_workflow_run_timestamp_pointer( output_pipeline_dir )
    print( f"[write_workflow_run_timestamp] {output_pipeline_dir / U.RUN_TIMESTAMP_POINTER_FILENAME} -> {suffix}" )


if __name__ == '__main__':
    main()
