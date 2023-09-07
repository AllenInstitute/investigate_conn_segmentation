#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 25 21:27:10 2023

@author: nicholas.lusk
"""

import os
import socket

import pandas as pd
import SimpleITK as sitk
import rescale_grid as rg

from glob import glob

#==============================================================================
# Initialize Pathways
#==============================================================================

# temp for during dev off of the hpc
# possibly want to remove "root" variable later
if socket.gethostname() == 'OSXLTQMY7CK':
    root = '/Users/nicholas.lusk/allen'
else:
    root = ''

# was specific conda enviornemnts now compiled into one
call_env = 'source activate segment_reprocess\n'

# pathway to scripts on the server
script_base = "/allen/programs/celltypes/workgroups/mct-t200/ViralCore/Nick_Lusk/investigate_conn_segmentation/code/"


# the path to the input .xlsx file and directory to where the reprocessed data will be saved
input_file = '/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/input/enhancers_dual_arber_3.xlsx'
base_directory = '/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/output/Dual_channel'

# create LIMS connection
conn = rg.initialize_connection()

#==============================================================================
# Main Loop
#==============================================================================
df = pd.read_excel(root + input_file)
channels = ['red', 'green']
std = 4

for iindex, irow in df.iterrows():
    
    #==========================================================================
    # Build directory for saving files
    #==========================================================================    
    
    image_series_id = irow['image_series_id']

    # Create output directory structure
    output_directory = os.path.join(base_directory, '%d/' % image_series_id )
    os.makedirs(root + output_directory, exist_ok = True )
    output_grid_directory = os.path.join( output_directory, 'grid' )
    os.makedirs(root + output_grid_directory, exist_ok = True )
    segmentation_red_directory = os.path.join( output_directory, 'segmentation_red' )
    os.makedirs(root + segmentation_red_directory, exist_ok = True )
    segmentation_green_directory = os.path.join( output_directory, 'segmentation_green' )
    os.makedirs(root + segmentation_green_directory, exist_ok = True )
    
    
    # Query LIMS for jp2 image path and write to file
    path_file = os.path.join(output_directory, 'image_paths.csv' )
    paths = rg.get_image_full_local_paths(image_series_id, conn)
    paths.to_csv( root + path_file, index=False )
    
    # Query LIMS for grid storage directory and save to new path
    iser = rg.get_image_series(image_series_id, conn)
    print(iser.storage_directory )
    
    input_grid_directory = os.path.join(iser.storage_directory, 'grid' )
    
    channel_opts = [os.path.basename(glob(os.path.join(root + input_grid_directory, 'red_2*.mhd'))[0]),
                       os.path.basename(glob(os.path.join(root + input_grid_directory, 'green_2*.mhd'))[0])]
    
    for in_opt in channel_opts:
        input_file = root + os.path.join(input_grid_directory, in_opt)
        output_file = root + os.path.join(output_grid_directory, in_opt)
        input_grid = sitk.ReadImage(input_file)
        sitk.WriteImage(input_grid, output_file)
    
    #==========================================================================
    # Create slurm batch file for running segmentation
    #==========================================================================
    
    script_file = root + os.path.join(output_directory, 'run_dual_segmentation.slurm')
    log_file = os.path.join(output_directory, 'run_dual_segmentation.log' )

    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=2 --mem=128G\n',
            '#SBATCH --time=5:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n',
            '#SBATCH --array=1-' + str(paths.shape[0] + 1) + '%32\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "run_dual_segmentation_%d" % image_series_id  + "\n"
        line += "#SBATCH --output=" + log_file + "\n\n"
        line += call_env + "\n"
        line += 'OUTPUT_PATH=' + output_directory + '\n'
        line += 'FILE=$(cat ' + path_file + ' | head -n $SLURM_ARRAY_TASK_ID | tail -n 1) \n\n'
        line += "python -m dual_quant $FILE $OUTPUT_PATH " + str(std)
        file.write(line)
    
    # Copy and modify grid json input file
    json_file = "TISSUECYTE_GRID_CLASSIC_QUEUE_%d_input.json" % image_series_id
    reference_file = os.path.join(os.path.dirname(input_grid_directory), json_file)

    output_files = []
    for ch in channels:
        json_new = "TISSUECYTE_GRID_CLASSIC_QUEUE_{0}_{1}_input.json".format(image_series_id, ch)
        output_file = os.path.join(output_directory, json_new)
        rg.modify_grid_json(root + reference_file, output_directory, root + output_file, ch)
        
        output_files.append(output_file)
    
    #==========================================================================
    # Create slurm batch file for running gridding
    #==========================================================================
        
    script_file = root + os.path.join( output_directory, 'run_gridding.slurm'  )
    log_file = os.path.join( output_directory, 'run_gridding.log' )
    
    with open( script_file, 'w', encoding =' utf-8' ) as file :
    
        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=8 --mem=128G\n',
            '#SBATCH --time=10:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n']
                
        file.writelines(job_settings)
            
        line = "#SBATCH --job-name=" + "grid_connseg_%d" % image_series_id  + "\n"
        line += "#SBATCH --output=" + log_file + "\n\n"
        file.write(line)
        
        for c, output_file in enumerate(output_files):
            
            gridding_output = os.path.join( output_directory, 'gridding_output_' + channels[c] + '.json' )
            
            line = "/allen/aibs/technology/conda/run_miniconda.sh /allen/aibs/technology/conda/production/allensdk_internal_temp2 python -m allensdk.mouse_connectivity.grid --case classic "
            line += "--input_json "
            line += output_file + " "
            line += "--output_json "
            line += gridding_output + " \n\n"
            
            if c == 0:
                
                line += "basedir=" + os.path.join(base_directory, str(image_series_id), 'grid') + "\n"
                line += 'mv "$basedir"/accumulators "$basedir"/accumulators_red\n\n'
                line += 'mkdir "$basedir"/nrrd_red\n\n'
                line += 'for file in "$basedir"/*.nrrd\n'
                line += "do\n"
                line += '  fname=$(basename $file)\n'
                line += '  mv "$file" "${basedir}/nrrd_red/${fname%%.*}_red.nrrd"\n'
                line += "done\n\n"
            elif c == 1:
                
                line += 'mv "$basedir"/accumulators "$basedir"/accumulators_green\n\n'
                line += 'mkdir "$basedir"/nrrd_green\n\n'
                line += 'for file in "$basedir"/*.nrrd\n'
                line += "do\n"
                line += '  fname=$(basename $file)\n'
                line += '  mv "$file" "${basedir}/nrrd_green/${fname%%.*}_green.nrrd"\n'
                line += "done\n\n"
                
                
            file.write(line)
        
        
    # Copy and modify unionize json input file
    json_file = "TISSUECYTE_UNIONIZE_CLASSIC_QUEUE_%d_input.json" % image_series_id
    reference_file = os.path.join(os.path.dirname(input_grid_directory), json_file)
    
    output_files = []
    for ch in channels:
        json_new = "TISSUECYTE_UNIONIZE_CLASSIC_QUEUE_{0}_{1}_input.json".format(image_series_id, ch)
        output_file = os.path.join( output_directory, json_new)
        rg.modify_unionize_json(root + reference_file, output_directory, root + output_file, ch)
        
        output_files.append(output_file)
        
    #==========================================================================
    # Create slurm batch file for running unionization
    #==========================================================================
        
    script_file = root + os.path.join(output_directory, 'run_unionize.slurm'  )
    log_file = os.path.join(output_directory, 'run_unionize.log' )

     
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
        
        for c, output_file in enumerate(output_files):
            
            unionize_output = os.path.join(output_directory, 'unionize_output_' + channels[c] + '.json' )
            reformatted_output = os.path.join(output_directory, 'formatted_unionize_' +channels[c] + '.csv' )
            
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
            line += reformatted_output + "\n\n"
            file.write(line)
            

if conn is not None :
    conn.close()    