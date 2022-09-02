from rescale_grid import *
import os
import shutil
import pandas as pd

connseg_python_exe = "/home/lydian/anaconda3/envs/connseg/bin/python"
testglymur_python_exe = "/home/lydian/anaconda3/envs/testglymur/bin/python"

script_base = "/allen/aibs/informatics/lydian/investigate_conn_segmentation/code/"

module_path = "/shared/bioapps/infoapps/lims2_modules/mouseconn/ProjectionSegmenter/bin/ProjectionSegmenter"

base_directory = '/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/output'
input_file = '/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/input/202208251628_brains_seg_rest_high.xlsx'


df = pd.read_excel(input_file)

for iindex, irow in df.iterrows() :

    image_series_id = irow['image_series_id']

    # Create output directory structure
    output_directory = os.path.join( base_directory, '%d/' % image_series_id )
    os.makedirs( output_directory, exist_ok = True )
    output_grid_directory = os.path.join( output_directory, 'grid' )
    os.makedirs( output_grid_directory, exist_ok = True )
    rescale_image_directory = os.path.join( output_directory, 'rescaled' )
    os.makedirs( rescale_image_directory, exist_ok = True )
    segmentation_directory = os.path.join( output_directory, 'segmentation' )
    os.makedirs( segmentation_directory, exist_ok = True )


    # Query LIMS for grid storage directory
    conn = initialize_connection()
    iser = get_image_series( image_series_id, conn )
    print( iser.storage_directory )

    input_grid_directory = os.path.join( iser.storage_directory, 'grid' )
    

    # Rescale intensity for base on method
    channel_scale = {}
    channel_scale['red_28.mhd'] = 1.0
    
    if irow['method'] == "high_green" :
        # Rescale intensity for "high green" cases
        channel_scale['green_28.mhd'] = 0.3
    elif irow['method'] == "low_green" :
        # rescale intensity for "low green" cases
        channel_scale['green_28.mhd'] = 4.0

    for c in channel_scale :
        input_file = os.path.join( input_grid_directory, c )
        output_file = os.path.join( output_grid_directory, c )
        rescale_grid( input_file, channel_scale[c], output_file )


    # Query LIMS for jp2 image path and write to file
    path_file = os.path.join( output_directory, 'image_paths.csv' )
    paths = get_image_full_local_paths( image_series_id, conn )
    paths.to_csv( path_file, index=False )
    
    # Create slurm batch file for running rescaling 
    script_file = os.path.join( output_directory, 'run_rescaling.slurm'  )
    log_file = os.path.join( output_directory, 'run_rescaling.log' )
    
    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=1 --mem=16G\n',
            '#SBATCH --time=5:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "run_rescaling_%d" % image_series_id  + "\n"
        file.write(line)

        line = "#SBATCH --output=" + log_file + "\n"
        file.write(line)

        line = testglymur_python_exe + " "
        line += os.path.join( script_base, 'batch_rescale_jp2.py' )
        line += " "
        line += str( output_directory )
        line += " "
        line += str(channel_scale['green_28.mhd'])
        file.write(line)


    # Create slurm batch file for running segmentation
    script_file = os.path.join( output_directory, 'run_segmentation.slurm'  )
    log_file = os.path.join( output_directory, 'run_segmentation.log' )

    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=1 --mem=16G\n',
            '#SBATCH --time=5:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "run_segmentation_%d" % image_series_id  + "\n"
        file.write(line)

        line = "#SBATCH --output=" + log_file + "\n"
        file.write(line)

        
        for pindex, prow in paths.iterrows() :
        
            bname = os.path.basename( prow['full_local_path'] )
            barr = os.path.splitext( bname )
            input_file = os.path.join( rescale_image_directory, bname )
            
            ofile = barr[0] + "_projection.jp2"
            output_file = os.path.join( segmentation_directory, ofile )
            
            line = module_command( module_path, input_file, output_grid_directory, output_file )
            
            file.write( line )
                  
                  
                  
    # Copy and modify grid json input file
    json_file = "TISSUECYTE_GRID_CLASSIC_QUEUE_%d_input.json" % image_series_id
    reference_file = os.path.join( input_grid_directory, "..", json_file )
    output_file = os.path.join( output_directory, json_file )
    modify_grid_json( reference_file, output_directory, output_file )


    # Create slurm batch file for running gridding
    script_file = os.path.join( output_directory, 'run_gridding.slurm'  )
    log_file = os.path.join( output_directory, 'run_gridding.log' )
    gridding_output = os.path.join( output_directory, 'gridding_output.json' )

    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=8 --mem=248G\n',
            '#SBATCH --time=10:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "grid_connseg_%d" % image_series_id  + "\n"
        file.write(line)

        line = "#SBATCH --output=" + log_file + "\n"
        file.write(line)

        line = "/allen/aibs/technology/conda/run_miniconda.sh /allen/aibs/technology/conda/production/allensdk_internal_temp2 python -m allensdk.mouse_connectivity.grid --case classic "
        line += "--input_json "
        line += output_file + " "
        line += "--output_json "
        line += gridding_output + " "
        file.write(line)
    
    
    # Copy and modify unionize json input file
    json_file = "TISSUECYTE_UNIONIZE_CLASSIC_QUEUE_%d_input.json" % image_series_id
    reference_file = os.path.join( input_grid_directory, "..", json_file )
    output_file = os.path.join( output_directory, json_file )
    modify_unionize_json( reference_file, output_directory, output_file )

    # Create slurm batch file for running unionization
    script_file = os.path.join( output_directory, 'run_unionize.slurm'  )
    log_file = os.path.join( output_directory, 'run_unionize.log' )
    unionize_output = os.path.join( output_directory, 'unionize_output.json' )
    reformatted_output = os.path.join( output_directory, 'formatted_unionize.csv' )
 
    with open( script_file, 'w', encoding =' utf-8' ) as file :

        job_settings = [
            '#!/bin/bash\n',
            '#SBATCH --partition=celltypes\n',
            '#SBATCH --nodes=1 --cpus-per-task=1 --mem=64G\n',
            '#SBATCH --time=7:00:00\n',
            '#SBATCH --export=NONE\n',
            '#SBATCH --mail-type=NONE\n']
            
        file.writelines(job_settings)
        
        line = "#SBATCH --job-name=" + "unionize_connseg_%d" % image_series_id  + "\n"
        file.write(line)

        line = "#SBATCH --output=" + log_file + "\n"
        file.write(line)

        line = "/allen/aibs/technology/conda/run_miniconda.sh /allen/aibs/technology/conda/production/tc_stitch_legacy_27 python -m allensdk.internal.pipeline_modules.run_tissuecyte_unionize_classic_from_json "
        line += output_file + " "
        line += unionize_output + "\n"
        file.write(line)
        
        line = connseg_python_exe + " "
        line += os.path.join( script_base, 'reformat_unionize.py' )
        line + " "
        line += str(image_series_id) + " "
        line += unionize_output + " "
        line += reformatted_output + "\n"
        file.write(line)
        

    if conn is not None :
        conn.close()