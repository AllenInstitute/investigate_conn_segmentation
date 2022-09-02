#!/usr/bin/python

import sys, getopt
from rescale_grid import *
import json
import pandas as pd

def reformat( image_series_id, input_file, output_file ) :

    # print( image_series_id )

    # base_directory = '/allen/scratch/aibstemp/lydian/investigate_connseg/'

    # output_directory = os.path.join( base_directory, str(image_series_id) )
    # input_file = os.path.join( output_directory, 'unionize_output.json' )
    # output_file = os.path.join( output_directory, 'formatted_unionize.csv' )
    
    conn = initialize_connection()
    iser = get_image_series( image_series_id, conn )
    
    structures = get_structures( conn )
    structures.set_index('id', inplace=True )
    
    hemispheres = get_hemispheres( conn )
    hemispheres.set_index('id', inplace=True )
            
    df = pd.read_json( input_file )
    df['specimen'] = iser['specimen_name']

    for findex, frow in df.iterrows() :
        df.loc[findex,'structure'] = structures.loc[frow['structure_id'], 'acronym']
        df.loc[findex,'graph_order'] = structures.loc[frow['structure_id'], 'graph_order']
        df.loc[findex,'hemisphere'] = hemispheres.loc[frow['hemisphere_id'], 'name' ]
        

    keep_cols = ['specimen','image_series_id','structure','graph_order','hemisphere','is_injection','projection_volume']
    filtered = df.loc[:,keep_cols]
   
    filtered.to_csv( output_file, index=False )

    
    if conn is not None :
        conn.close()


if __name__ == "__main__":
   reformat(int(sys.argv[1]),sys.argv[2],sys.argv[3])
