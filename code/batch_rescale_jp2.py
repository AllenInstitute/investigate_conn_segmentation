#!/usr/bin/python

import os
import sys
import glymur

import numpy as np
import pandas as pd

#===============================================================================
# Load jp2 and scale green channel
#===============================================================================
def rescale_jp2(inputfile, g_scale, r_scale, mask, tessellation, outputfile) :

    jp2 = glymur.Jp2k(inputfile)
    fullres = jp2[:]
    
    # eliminates strange overexposure that can occure around tissue edge
    # current cut-off is 1000 in R and G channel but may need to be moved around
    if mask:
        row, col = np.where((fullres[:, :, 0] > 1000) & (fullres[:, :, 1] > 1000))
        fullres[row, col, :] = 0
    
    # helps minimize tessellation from inconsistant brightness across stitched images
    # numbers are arbitrary just using what seems to work
    if tessellation:
        img = fullres[:, :, 1]
        edge_img = cv2.Canny(img, 150 * 2**8, 200 * 2**8, apertureSize = 3)
        row, col = np.where(edge_img > 0)
        fullres[row, col, 1] = img[row, col] / 3

    fullres[:,:,0] = np.around(np.multiply( fullres[:,:,0], r_scale))
    
    if g_scale <= 1:
        fullres[:,:,1] = np.around(np.multiply( fullres[:,:,1], g_scale))
    else:
        g_denom = np.max(fullres[:, :, 1]) / g_scale
        g_scaled = np.exp(fullres[:, :, 1] / g_denom) - 1
        g_norm = (g_scaled - np.min(g_scaled)) / (np.max(g_scaled) - np.min(g_scaled)) * 65535
        
        fullres[:, :, 1] = np.around(g_norm)

    glymur.Jp2k(outputfile, fullres)

#===============================================================================
# Main function looping through jp2 pathways
#===============================================================================
def batch_rescale(output_directory, g_scale, r_scale, mask) :
    
    # number of cores you have allocated for your slurm task:
    number_of_cores = int(os.environ['SLURM_CPUS_PER_TASK'])
    glymur.set_option('lib.num_threads', number_of_cores)
   
    path_file = os.path.join(output_directory, 'image_paths.csv' )
    paths = pd.read_csv( path_file )

    for pindex, prow in paths.iterrows() :

        bname = os.path.basename(prow['full_local_path'])
        output_file = os.path.join( output_directory, 'rescaled', bname )

        print(bname)
        rescale_jp2( prow['full_local_path'], g_scale, r_scale, mask, output_file )

    print('Rescaling Completed: Success')

if __name__ == "__main__":
    
    # backwards compatable with scripts pre-mask installment
    if len(sys.argv) < 5:
        batch_rescale(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), False, False)
    elif: len(sys.argv) == 5:
        batch_rescale(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), bool(sys.argv[4]), False)
    else:
        batch_rescale(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), bool(sys.argv[4]), bool(sys.argv[5]))