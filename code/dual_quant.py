#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  5 16:18:24 2023

@author: nicholas.lusk
"""
import os
import cv2
import sys
import glymur

import numpy as np
import albumentations as alb

from PIL import Image
from scipy.signal import argrelextrema
from skimage import img_as_float
from skimage.morphology import reconstruction
from scipy.interpolate import UnivariateSpline
from scipy.ndimage import gaussian_filter, gaussian_filter1d

# initialize module parameters
Image.MAX_IMAGE_PIXELS = 12000000000
glymur.set_option('lib.num_threads', os.cpu_count() - 2)


#==============================================================================
# Image Processing Functions
#==============================================================================

def bkg_subtract(img, bkg):
    
    transform = alb.Compose([
        alb.ToFloat(max_value = 65535.0),
        alb.MedianBlur((5, 5), always_apply = True),
        alb.GaussianBlur((7,7), p=1.0),
        alb.FromFloat(max_value=65535.0)
        ]
    )
    
    smooth_bkg = transform(image = bkg)
    img -= smooth_bkg['image']
    img = np.clip(img, 0, img.max())

    return img.astype("uint16")

# version 4 using albumentation
def get_border(img):
    
    print("smoothing pipeline")
    transform = alb.Compose([
        alb.ToFloat(max_value = 65535.0),
        alb.MedianBlur((5, 5), always_apply = True),
        alb.augmentations.transforms.UnsharpMask((11, 11), always_apply = True),
        alb.FromFloat(max_value=65535.0)
        ]
    )
            
    transformed = transform(image = img)
    img_sharp = transformed['image']

    img_8bit = np.uint8((img_sharp - img_sharp.min()) / (img_sharp.max() - img_sharp.min()) * 255)
    img_8bit = cv2.GaussianBlur(img_8bit, (11, 11), 5)
    
    cnts, _ = cv2.findContours(img_8bit.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnts_sort = sorted(cnts, key=cv2.contourArea, reverse = True)
    
    cnts_keep = []
    for c in cnts_sort:
        if len(c) > 15000:
            cnts_keep.append(c)
        else:
            break
        
    img_border = np.zeros(img.shape)
    mask = np.zeros((img.shape[0] + 2, img.shape[1] + 2), 'uint8')
    cv2.drawContours(img_border, cnts_keep, -1, (255, 255, 225), 1) 
    
    # get line for boarder    
    img_fill = cv2.floodFill(img_border.astype('uint8'), mask, (0, 0), 255)
    img_inv = cv2.bitwise_not(img_fill[1])
    
    img_dil = cv2.dilate(img_inv, np.ones((25, 25)), iterations = 3)    
    img_out = np.where(img_inv != img_dil, 64, 0)
    
    return img_out.astype('uint8'), img_inv

def get_boundingbox(mask, pad = 100):
    
    loc = np.where(mask > 0)
    
    bounds = [np.min(loc[0]) - pad,
              np.max(loc[0]) + pad,
              np.min(loc[1]) - pad,
              np.max(loc[1]) + pad]
    
    return bounds

def get_stats(img, mask):
        
    loc = np.where(mask > 0)
    vals = img[loc]
    count, bin_count = np.histogram(vals, bins = 2**16, range = (0, 2**16), density = True)
    count_hat = gaussian_filter1d(count, 20)
        
    # get max vals by finding greatest point +- 100 steps each side
    maximas = argrelextrema(count_hat, np.greater, order = 100)[0]
    
    difference = np.diff(count_hat)
    diff_maximas = argrelextrema(difference, np.greater, order = 100)[0]
    
    if diff_maximas[0] < maximas[0] and diff_maximas[1] > maximas[0]:
        maxima = maximas[0]
    else:
        maxima = diff_maximas[0]
    
    # get the max peak and get std by taking only data larger
    # std calculated from half of a distribution is the same as the whole
    # removed since STD drastically affected by strong signal. moved to FWHM
    #rel_data = vals[vals >= maxima]
    #std = np.std(rel_data)
    
    #not using Std due to skewness with high signal using FWHM instead
    spline = UnivariateSpline(bin_count[1:], count_hat-count_hat[maxima]/2, s=0)
    roots = spline.roots()
    std = roots[-1]

    return std, maxima

# blur and threshold image for signal detection
def process(img, mask, std = 6):
    
    popt = get_stats(img, mask)
    thresh = popt[1] + std * popt[0]
    
    while thresh >= 65535:
        std -= 0.1
        thresh = popt[1] + std * popt[0]
    
    img_thresh = np.where(img > thresh, 224, 0)
    
    img_med = cv2.medianBlur(img_thresh.astype('uint8'), 5)
    img_close = cv2.morphologyEx(img_med, cv2.MORPH_CLOSE, np.ones((5,5)))
    img_open = cv2.morphologyEx(img_close, cv2.MORPH_OPEN, np.ones((5,5)))
    
    return img_open

#==============================================================================
# Main Function
#==============================================================================
    
def main(image, out_path, std):
    """
    Takes list of image series to be processed
    """
    
    channels = ['red', 'green']
    print(image)
    
    img = glymur.Jp2k(image)
    img = img[:]
    
    clahe = cv2.createCLAHE(clipLimit = 10, tileGridSize = (300, 400))
    
    img_bkg = clahe.apply(img[:, :, 1])
    
    print("Identifying border...\n")
    boarder, mask = get_border(img_bkg)

    img_blue = img[:, :, 2]
    img_blue = np.where(img_blue > 5000, 65535, img_blue)
    
    for c, ch in enumerate(channels):
        
        img_ch = img[:, :, c].astype(float)

        # subtract blue channel
        img_ch = bkg_subtract(img_ch, img_blue)
          
        print("Processing images...\n")            
        img_out = process(img_ch, mask, std = float(std))
        img_save = np.array(img_out)
        
        img_save = np.where(boarder > 0, boarder, img_save)

        print("Saving channel images...\n")        
        img_root = os.path.basename(image)
        save_name = img_root[:-4] + "_projection_" + ch
        save_file = os.path.join(out_path, 'segmentation_' + ch, save_name + '.jp2')
        
        print(save_file)
        glymur.Jp2k(save_file, img_save)
            
    return 

if __name__ == "__main__":
   main(sys.argv[1], sys.argv[2], sys.argv[3])

