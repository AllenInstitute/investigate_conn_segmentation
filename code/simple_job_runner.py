import os
import pandas as pd
import subprocess

## you need to run this on hpc-login server in order to submit slurm jobs

base_directory = '/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/output'
input_file = '/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/input/202208251628_brains_seg_rest_high.xlsx'

module_to_run = 'rescaling'  # takes around 3 hrs - can be broken up into image bundles
#module_to_run = 'segmentation' # takes around 2.5 hrs - can be broken up into image bundles
#module_to_run = 'gridding' # takes around 1.5 hrs - cannot be further broken down, can add more cores
#module_to_run = 'unionize' # takes around 15 mins - cannot be further broken down, can add more cores

df = pd.read_excel(input_file)
ilist = list(df['image_series_id'].values)

for image_series_id in ilist :

    script_file = os.path.join( base_directory, str(image_series_id), 'run_%s.slurm' % module_to_run )
    
    if os.path.isfile( script_file ) :
        cmd = ['sbatch',script_file]
        subprocess.run(cmd)
        print("processing :" + script_file)
    else :
        print("file not found: " + script_file )
    
    
