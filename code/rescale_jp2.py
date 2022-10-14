import os
import glymur
import numpy as np


def rescale_jp2( inputfile, scale, outputfile ) :
    
    # number of cores you have allocated for your slurm task:
    number_of_cores = int(os.environ['SLURM_CPUS_PER_TASK'])
    glymur.set_option('lib.num_threads', number of cores)
    
    input = glymur.Jp2k(inputfile)
    fullres = input[:]
    fullres[:,:,1] = np.around(np.multiply( fullres[:,:,1], scale ))
 
    output = glymur.Jp2k(outputfile)
    output[:] = fullres

