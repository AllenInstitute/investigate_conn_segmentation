import os
#import glymur
import numpy as np
import psycopg2
import pandas as pd
import SimpleITK as sitk

'''
def rescale_jp2( inputfile, scale, outputfile ) :

    jp2 = glymur.Jp2k(inputfile)
    fullres = jp2[:]
    fullres[:,:,1] = np.multiply( fullres[:,:,1], scale )

    jp2 = glymur.Jp2k(outputfile)
    jp2[:] = fullres
'''
    
    
def rescale_grid( inputfile, scale, outputfile ) :

    input = sitk.ReadImage( inputfile )

    output = sitk.Cast( input, sitk.sitkFloat32 )
    output = sitk.Multiply( output, scale )
    output = sitk.Cast( output, sitk.sitkUInt16 )

    sitk.WriteImage( output, outputfile )

    
def initialize_connection() :
    conn = psycopg2.connect("host=limsdb3 dbname=lims2 user=atlasreader password=atlasro")
    return conn
    
def get_image_full_local_paths( image_series_id, conn ) :
    query = '''
        select sl.storage_directory || img.jp2 as full_local_path
        from image_series_slides iss
        join slides sl on iss.slide_id = sl.id
        join images img on img.slide_id = sl.id and img.image_type_id = 1 
        where iss.image_series_id = %d
        order by jp2
        ''' % image_series_id
    res = pd.read_sql_query(query,conn)
    return res
    
def get_image_series( image_series_id, conn ) :
    query = '''
        select iser.*
        from image_series iser
        where iser.id = %d
        ''' % image_series_id
        
    res = pd.read_sql_query(query,conn)
    if len(res) > 0 :
        return res.loc[0]
    else :
        return None