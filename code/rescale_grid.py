import os
import numpy as np
import psycopg2
import pandas as pd
import SimpleITK as sitk
import json
    
def rescale_grid( inputfile, scale, outputfile, flip, enu) :
    
    options = ['red_22.4.mhd',
               'green_22.4.mhd']
    
    input = sitk.ReadImage(inputfile)

    output = sitk.Cast(input, sitk.sitkFloat32)
    output = sitk.Multiply( output, scale)
    output = sitk.Cast(output, sitk.sitkUInt16)
    
    if flip:
        base = os.path.dirname(outputfile)
        if enu == 0:
            outputfile = os.path.join(base, options[1])
        else:
            outputfile = os.path.join(base, options[0])
    else:
        print('did not flip')
            
    sitk.WriteImage(output, outputfile)
    
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
        select iser.*, sp.name as specimen_name
        from image_series iser
        join specimens sp on iser.specimen_id = sp.id
        where iser.id = %d
        ''' % image_series_id
        
    res = pd.read_sql_query(query,conn)
    if len(res) > 0 :
        return res.loc[0]
    else :
        return None
        
        
def get_structures( conn ) :
    query = '''
        select st.*
        from flat_structures_v st
        where st.graph_id = 1
        '''
    res = pd.read_sql_query(query,conn)
    return res
     
     
def get_hemispheres( conn ) :
    query = '''
        select h.*
        from hemispheres h
        '''
    res = pd.read_sql_query(query,conn)
    return res
        
        
def module_command( module_path, input_file, grid_directory, output_file ) :

    '''
    http://stash.corp.alleninstitute.org/projects/INF/repos/lims2_modules/browse/mouseconn/ProjectionSegmenter/ProjectionSegmenter.cpp#193
    /shared/bioapps/infoapps/lims2_modules/mouseconn/ProjectionSegmenter/bin/ProjectionSegmenter

      Allowed options:
      --help                          print help message
      -i [ --inputImage ] arg         input image
      -b [ --inputBImage ] arg        input Bimage
      -m [ --inputEstimate ] arg      input estimate
      -o [ --outputFile ] arg         output image/file
      -B [ --outputBFile ] arg        output Bimage/file
      -g [ --inputGrid ] arg          input grid directory
      -a [ --inputRegionXml ] arg     input regionxml
      -s [ --inputsenslevelfile ] arg input sensitivitylevel file
      -d [ --disk ] arg               disk partion for image_series
      -l [ --lossless ]               write lossless JP2
      -n [ --normalization ]          normalize intensity
      -N [ --nodownsample ]           No downsample
      -1 [ --onepass ]                1-pass processing
      -e [ --estimatefromfullonly ]   estimate section peaks
      -E [ --estimatefromgridonly ]   estimate all middle section peaks from grid only
      -M [ --estimatefromgrid ]       apply peaks from grid
      -r [ --bitrate ] arg            target JP2 bitrate
      -R [ --rpeak ] arg              section Rpeak
      -G [ --gpeak ] arg              section Gpeak
      -S [ --sensitivitylevel ] arg   sensitivityLevel setting
      -c [ --Aim5_OP_code ] arg       Aim5_OP_code setting
      -A [ --Aim ] arg                processAim (1(default),3, 40(Rsoma), 41(G), 5
      -D [ --sectionDepth ] arg       sectionDepth (40 or 90)
      -f [ --ftroutput ]              output features
      -t [ --trainingMode ]           png and features for traning
      -F [ --NOpostfilter ]           NOT perform post filtering
'''

    # Assemble module command line parameters
    margs = {}
    margs['Aim'] = '501'
    margs['normalization'] = '' # turning off makes the results worse
    margs['estimatefromgrid'] = ''
    margs['onepass'] = '' # turning off makes the results unusable
    margs['inputImage'] = input_file
    margs['outputFile'] = output_file
    margs['inputGrid'] = grid_directory
    margs['sensitivitylevel'] = '1' # has no effect when Aim = '501'

    line = module_path + " "
    for a in margs :
        line += "--" + a + " " + margs[a] + " "
    line += "\n"
    
    return line
    
    
def modify_grid_json( input_json, output_directory, output_json ) :

    # Read input json
    with open( input_json, "r" ) as file :
        data = json.load( file )
        
    # Modify output directories
    data['storage_directory'] = output_directory
    data['grid_prefix'] = os.path.join( output_directory, 'grid' )
    data['accumulator_prefix'] = os.path.join( output_directory, 'grid', 'accumulators' )
    
    # Modify json for each sub_image
    slist = data['sub_images']
    for si in slist :
                
        bname = os.path.basename( si['segmentation_paths']['segmentation'] )
        si['segmentation_paths']['segmentation'] = os.path.join( output_directory, 'segmentation', bname )

    # Write output json
    with open( output_json, "w" ) as file :
        json.dump( data, file, indent = 4 )
        
        
def modify_unionize_json( input_json, output_directory, output_json ) :

    # Read input json
    with open( input_json, "r" ) as file :
        data = json.load( file )
        
    glist = data['grid_paths']
    
    for g in glist :
        bname = os.path.basename( glist[g] )
        if '_intensities' in g or '_pixels' in g:
            glist[g] = os.path.join( output_directory, 'grid', 'accumulators', bname )
        else :
            glist[g] = os.path.join( output_directory, 'grid', bname )
       

    # Write output json
    with open( output_json, "w" ) as file :
        json.dump( data, file, indent = 4 )
