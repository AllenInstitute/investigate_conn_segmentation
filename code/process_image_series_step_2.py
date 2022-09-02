from rescale_jp2 import *
import pandas as pd

base_directory = '/allen/scratch/aibstemp/lydian/investigate_connseg/'
#image_series_id = 1144635698
#image_series_id = 1121032541
ilist = [1121227875, 1122764024, 1123120012, 1124377682, 1125851649, 1126038314, 1128921891]
scale = 0.3

for image_series_id in ilist :
    output_directory = os.path.join( base_directory, str(image_series_id) )

    path_file = os.path.join( output_directory, 'image_paths.csv' )
    paths = pd.read_csv( path_file )

    for pindex, prow in paths.iterrows() :

        bname = os.path.basename(prow['full_local_path'])
        output_file = os.path.join( output_directory, 'rescaled', bname )

        print(bname)
        rescale_jp2( prow['full_local_path'], scale, output_file )


