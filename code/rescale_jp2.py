import os
import glymur
import numpy as np


def rescale_jp2( inputfile, scale, outputfile ) :

    input = glymur.Jp2k(inputfile)
    fullres = input[:]
    fullres[:,:,1] = np.around(np.multiply( fullres[:,:,1], scale ))
 
    output = glymur.Jp2k(outputfile)
    output[:] = fullres

