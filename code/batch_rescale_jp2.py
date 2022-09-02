#!/usr/bin/python

import sys, getopt
from rescale_jp2 import *
import pandas as pd


def batch_rescale( output_directory, scale ) :

    #scale = 0.3
    #scale = 4.0

    path_file = os.path.join( output_directory, 'image_paths.csv' )
    paths = pd.read_csv( path_file )

    for pindex, prow in paths.iterrows() :

        bname = os.path.basename(prow['full_local_path'])
        output_file = os.path.join( output_directory, 'rescaled', bname )

        print(bname)
        rescale_jp2( prow['full_local_path'], scale, output_file )


if __name__ == "__main__":
   batch_rescale(sys.argv[1], float(sys.argv[2]))
