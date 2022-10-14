
import os
import re
import socket

import pandas as pd

from glob import glob
from rescale_grid import *


#==============================================================================
# Initialize Pathways
#==============================================================================

# temp for during dev off of the hpc
# possibly want to remove "root" variable later
if socket.gethostname() == 'OSXLTSDQ05P':
    root = '/Users/nicholas.lusk'
else:
    root = ''

# was specific conda enviornemnts now compiled into one
call_env = 'source activate segment_reprocess\n'

# pathway to scripts on the server
script_base = "/allen/programs/celltypes/workgroups/mct-t200/ViralCore/Nick_Lusk/investigate_conn_segmentation/code/"

# don't know what this is, but must be related to LIMS
module_path = "/shared/bioapps/infoapps/lims2_modules/mouseconn/ProjectionSegmenter/bin/ProjectionSegmenter"

# the path to the input .xlsx file and directory to where the reprocessed data will be saved
# currently the input_file needs two columns: ['image_series_id', 'method']
    # method (str): 'high_green' or 'low_green
input_file = '/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/input/boaz_seg_subset.xlsx'
base_directory = '/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/output'

#==============================================================================
# Main Loop
#==============================================================================
df = pd.read_excel(root + input_file)

for iindex, irow in df.iterrows() :

    image_series_id = irow['image_series_id']

    # Create output directory structure
    output_directory = os.path.join(base_directory, '%d/' % image_series_id )
    os.makedirs(root + output_directory, exist_ok = True )
    output_grid_directory = os.path.join( output_directory, 'grid' )
    os.makedirs(root + output_grid_directory, exist_ok = True )
    rescale_image_directory = os.path.join( output_directory, 'rescaled' )
    os.makedirs(root + rescale_image_directory, exist_ok = True )
    segmentation_directory = os.path.join( output_directory, 'segmentation' )
    os.makedirs(root + segmentation_directory, exist_ok = True )


    # Query LIMS for grid storage directory
    conn = initialize_connection()
    iser = get_image_series(image_series_id, conn)
    print(iser.storage_directory )

    input_grid_directory = os.path.join(iser.storage_directory, 'grid' )
    
    # Check the channels voxelation and rescale intensity for base on method
    channel_opts = [os.path.basename(glob(os.path.join(root + input_grid_directory, 'red_2*.mhd'))[0]),
                       os.path.basename(glob(os.path.join(root + input_grid_directory, 'green_2*.mhd'))[0])]
    
    channel_scale = {}
    channel_scale[channel_opts[0]] = 1.0
    
    if irow['method'] == "very_high_green" :
        # Rescale intensity for "very high green" cases (10000+)
        channel_scale[channel_opts[1]] = 0.2
    elif irow['method'] == "high_green" :
        # Rescale intensity for "high green" cases (9999-3000)
        channel_scale[channel_opts[1]] = 0.3
    elif irow['method'] == "low_green" :
        # rescale intensity for "low green" cases (<1500)
        channel_scale[channel_opts[1]] = 1.0
    elif irow['method'] == "very_low_green" :
        # rescale intensity for "low green" cases (<1500)
        channel_scale[channel_opts[1]] = 2.0
        

    for c in channel_scale :
        input_file = root + os.path.join( input_grid_directory, c )
        output_file = root + os.path.join( output_grid_directory, c )
        rescale_grid(input_file, channel_scale[c], output_file )


    # Query LIMS for jp2 image path and write to file
    path_file = os.path.join( output_directory, 'image_paths.csv' )
    paths = get_image_full_local_paths( image_series_id, conn )
    paths.to_csv( root + path_file, index=False )
    
    #==========================================================================
    # Create slurm batch file for running rescaling 
    #==========================================================================
    
    script_file = root + os.path.join(output_directory, 'run_rescaling.slurm')
    log_file = os.path.join(output_directory, 'run_rescaling.log' )
    
    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=16 --mem=32G\n',
            '#SBATCH --time=10:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "run_rescaling_%d" % image_series_id  + "\n"
        file.write(line)

        line = "#SBATCH --output=" + log_file + "\n\n"
        file.write(line)

        line = call_env # Was a specific Lydia environment. Made generic
        line += 'cd ' + script_base + '\n'
        line += 'python -m batch_rescale_jp2 '
        line += str( output_directory ) + ' '
        line += str(channel_scale[channel_opts[1]]) + ' ' + str(channel_scale[channel_opts[0]]) 
        file.write(line)

    #==========================================================================
    # Create slurm batch file for running segmentation
    #==========================================================================
    
    script_file = root + os.path.join(output_directory, 'run_segmentation.slurm')
    log_file = os.path.join(output_directory, 'run_segmentation.log' )

    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=1 --mem=16G\n',
            '#SBATCH --time=5:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n',
            '#SBATCH --array=0-' + str(paths.shape[0] - 1) + '%32\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "run_segmentation_%d" % image_series_id  + "\n"
        line += "#SBATCH --output=" + log_file + "\n\n"
        line += call_env + "\n"
        line += 'INPUT_FILES=(' + os.path.join(rescale_image_directory, '*.jp2') + ')\n'
        line += 'OUTPUT_PATH=' + segmentation_directory + '/\n\n'
        line += 'FILE=${INPUT_FILES[$SLURM_ARRAY_TASK_ID]}\n'
        line += 'FILENAME=${FILE##*/}\n'
        line += 'FILENAME_OUT=${FILENAME%.*}_projection.${FILENAME##*.}\n\n'
        file.write(line)
            
        line = module_command(module_path, '$FILE', output_grid_directory, '$OUTPUT_PATH$FILENAME_OUT' )            
        file.write( line )
        
    #==========================================================================
    # Create slurm batch file for running segmentation postprocessing
    #==========================================================================       
    
    script_file = root + os.path.join(output_directory, 'run_segmentation_cleanup.slurm')
    log_file = os.path.join(output_directory, 'run_segmentation_cleanup.log' )

    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=1 --mem=16G\n',
            '#SBATCH --time=5:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n',
            '#SBATCH --array=0-' + str(paths.shape[0] - 1) + '%32\n',
            '#SBATCH --job-name=' + 'run_segmentation_cleanup_%d' % image_series_id  + "\n",
            '#SBATCH --output=' + log_file + '\n\n']
            
        file.writelines(job_settings)
        
        line = call_env
        line += 'cd ' + script_base + '\n\n'
        line += 'INPUT_FILES=(' + os.path.join(segmentation_directory, '*.jp2') + ')\n'
        line += 'OUTPUT_PATH=' + segmentation_directory + '/\n\n'
        line += 'python -m segmentation_cleanup ${INPUT_FILES[$SLURM_ARRAY_TASK_ID]}'
        file.write(line)

    # Copy and modify grid json input file
    json_file = "TISSUECYTE_GRID_CLASSIC_QUEUE_%d_input.json" % image_series_id
    reference_file = os.path.join(os.path.dirname(input_grid_directory), json_file)
    output_file = os.path.join( output_directory, json_file)
    modify_grid_json(root + reference_file, output_directory, root + output_file)
    
    #==========================================================================
    # Create slurm batch file for running gridding
    #==========================================================================
    
    script_file = root + os.path.join( output_directory, 'run_gridding.slurm'  )
    log_file = os.path.join( output_directory, 'run_gridding.log' )
    gridding_output = os.path.join( output_directory, 'gridding_output.json' )

    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=8 --mem=64G\n',
            '#SBATCH --time=10:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "grid_connseg_%d" % image_series_id  + "\n"
        line += "#SBATCH --output=" + log_file + "\n\n"
        file.write(line)

        line = "/allen/aibs/technology/conda/run_miniconda.sh /allen/aibs/technology/conda/production/allensdk_internal_temp2 python -m allensdk.mouse_connectivity.grid --case classic "
        line += "--input_json "
        line += output_file + " "
        line += "--output_json "
        line += gridding_output + " "
        file.write(line)
    
    
    # Copy and modify unionize json input file
    json_file = "TISSUECYTE_UNIONIZE_CLASSIC_QUEUE_%d_input.json" % image_series_id
    reference_file = os.path.join(input_grid_directory, "..", json_file)
    output_file = os.path.join( output_directory, json_file )
    modify_unionize_json(root + reference_file, output_directory, root + output_file)
    
    #==========================================================================
    # Create slurm batch file for running unionization
    #==========================================================================
    
    script_file = root + os.path.join(output_directory, 'run_unionize.slurm'  )
    log_file = os.path.join(output_directory, 'run_unionize.log' )
    unionize_output = os.path.join(output_directory, 'unionize_output.json' )
    reformatted_output = os.path.join(output_directory, 'formatted_unionize.csv' )
 
    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=2 --mem=128G\n',
            '#SBATCH --time=7:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "unionize_connseg_%d" % image_series_id  + "\n"
        file.write(line)

        line = "#SBATCH --output=" + log_file + "\n\n"
        file.write(line)

        line = "/allen/aibs/technology/conda/run_miniconda.sh /allen/aibs/technology/conda/production/tc_stitch_legacy_27 python -m allensdk.internal.pipeline_modules.run_tissuecyte_unionize_classic_from_json "
        line += output_file + " "
        line += unionize_output + "\n\n"
        file.write(line)
        
        line = call_env # Was a specific Lydia environment. Made generic
        line += 'cd ' + script_base + '\n'
        line += 'python -m reformat_unionize'
        line += " "
        line += str(image_series_id) + " "
        line += unionize_output + " "
        line += reformatted_output + "\n"
        file.write(line)
        

    if conn is not None :
        conn.close()