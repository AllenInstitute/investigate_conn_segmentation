#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  6 11:11:12 2022

@author: nicholas.lusk
"""

import os
import sys
import glymur

import numpy as np
import pandas as pd

from skimage.measure import label, regionprops_table

#==============================================================================

''' The segmentation script outputs a grayscale projection with a few unique 
    values and removes eroneous signal. The two important intensities are 64 
    and 224.
    
        64:     the boundary of the tissue. 
        224:    "True" fluorescent signal 
'''
#==============================================================================

# function to clean up projection image 
def cleanup(jp2_file):

    # number of cores you have allocated for your slurm task:
    number_of_cores = int(os.environ['SLURM_CPUS_PER_TASK'])
    glymur.set_option('lib.num_threads', number_of_cores)
    
    properties = ['label', 'area', 'coords']

    jp2_raw = glymur.Jp2k(jp2_file)[:]
    jp2_new = np.where(np.isin(jp2_raw, [64, 224]), jp2_raw, 0)
    
    img_64 = np.where(jp2_new == 64, 1, 0)
    label_64 = label(img_64)
    
    areas = pd.DataFrame(regionprops_table(label_64, properties = properties))
    areas = areas.sort_values(by = 'area', ascending = False, ignore_index = True)
        
    # some slides have distinct boundaries, but no more than 3
    if areas.shape[0] > 3: 
        coords = np.vstack(areas['coords'][3:].values)
        jp2_new[coords[:, 0], coords[:, 1]] = 0
        
    glymur.Jp2k(jp2_file, jp2_new)

if __name__ == '__main__':
    cleanup(sys.argv[1])
        
    




