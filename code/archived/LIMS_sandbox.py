#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 12 12:15:48 2022

@author: nicholas.lusk
"""

import os
import glymur

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from PIL import Image
from glob import glob
from tqdm import tqdm
from matplotlib import cm

glymur.set_option('lib.num_threads', 6)

low_path = '/Users/nicholas.lusk/Desktop/jp2_testing/low_green'
low_files = sorted(glob(os.path.join(low_path, '*.jp2')))

high_path = '/Users/nicholas.lusk/Desktop/jp2_testing/high_green'
high_files = sorted(glob(os.path.join(high_path, '*.jp2')))

jp2_input = '/Users/nicholas.lusk/allen/programs/celltypes/workgroups/mousecelltypes/wb_imaging/tc_reprocess/output/1141661733'
jp2_output = '/Users/nicholas.lusk/Desktop/jp2_testing/high_green'


glymur.set_option('lib.num_threads', os.cpu_count() - 1)


def download_jp2(input_path, output_path):
    
    df = pd.read_csv(os.path.join(os.path.join(input_path, 'image_paths.csv')))
    
    for file in tqdm(df['full_local_path'].tolist(), total = len(df)):
        fname = os.path.basename(file)   
        jp2 = glymur.Jp2k('/Users/nicholas.lusk' + file)
        glymur.Jp2k(os.path.join(output_path, fname), jp2[:])

def plot_both(df):

    fig, ax = plt.subplots()
    sns.scatterplot(x = 'low_mean_g', y = 'low_std_g', data = df, color = 'limegreen', ax = ax, label = 'Low Green')
    sns.scatterplot(x = 'high_mean_g', y = 'high_std_g', data = df, color = 'green', ax = ax, label = 'High Green')
    #sns.scatterplot(x = 'low_mean_r', y = 'low_std_r', data = df, color = 'salmon', ax = ax, label = 'Low Red')
    #sns.scatterplot(x = 'high_mean_r', y = 'high_std_r', data = df, color = 'red', ax = ax, label = 'High Red')
    
    lims = [np.min([ax.get_xlim(), ax.get_ylim()]),  # min of both axes
            np.max([ax.get_xlim(), ax.get_ylim()])]  # max of both axes
    
    ax.plot(lims, lims, 'k--', alpha=0.75, zorder=0)
    
    ax.set_ylabel('Standard Deviation')
    ax.set_xlabel('Mean Intensity')
    ax.legend(loc = 'right')
    sns.despine()
    
    fig, ax = plt.subplots()
    sns.scatterplot(x = 'low_mean_g', y = 'low_mean_r', data = df, color = 'limegreen', ax = ax, label = 'Low Green')
    sns.scatterplot(x = 'high_mean_g', y = 'high_mean_r', data = df, color = 'green', ax = ax, label = 'High Green')
    
    lims = [np.min([ax.get_xlim(), ax.get_ylim()]),  # min of both axes
            np.max([ax.get_xlim(), ax.get_ylim()])]  # max of both axes
    
    ax.plot(lims, lims, 'k--', alpha=0.75, zorder=0)
    ax.set_ylabel('Mean Red Intensity')
    ax.set_xlabel('Mean Green Instensity')
    sns.despine()

def plot_one(slides, scales = [1, 2, 3, 4, 5], kind = 'line'):
    
    colors = ['red', 'orange', 'green', 'blue', 'violet']
    path = '/Users/nicholas.lusk/Desktop/jp2_testing/low_green/graphs/'
    
    for c, slide in tqdm(enumerate(slides), total = len(slides)):
        
        fname = path + 'slide_' + str(c + 1) + '_' + kind + '_2.png'
        vals = np.unique(slide)
        
        fig, ax = plt.subplots()
        
        if kind == 'density':
            sns.distplot(x = vals, color = 'k', kde = True, hist = False,
                         label = 'raw intensity', kde_kws = {'linewidth': 2}, ax = ax)
        elif kind == 'line':
                sns.scatterplot(x = vals, y = vals, color = 'k', label = 'raw intensity', ax = ax)         
        for scale in scales:
        
            g_denom = np.max(vals) / scale
            g_scaled = np.exp(vals / g_denom) - 1
            g_norm = (g_scaled - np.min(g_scaled)) / (np.max(g_scaled) - np.min(g_scaled)) * 65535
            
            if kind == 'density':            
                sns.displot(x = g_norm, color = colors[scale - 1], kde = True, hist = False,
                             label = 'log_norm intensity', kde_kws = {'linewidth': 2}, ax = ax)
                ax.set_xlim([0, 30000])
            elif kind == 'line':
                sns.scatterplot(x = vals, y = g_norm, color = 'r', label = 'log intensity', 
                                ax = ax)       
                ax.axvline(373, 0, .373, color = 'k')
                ax.axvline(580, 0, .373, color = 'r')
                ax.axhline(y = 373, color = 'k', linestyle = '--')
                ax.set_xlim([0, 1000])
                ax.set_ylim([0, 1000])
        
        sns.despine()
        plt.savefig(fname)
        plt.close()

# import path to cropped image
def plot_mesh(path, stride = 5):
    
    img = Image.open(path)
    img_array = np.asarray(img)
    
    # round values down to the nearest 10's
    width, height = img.size
    width, height = width - width % 10, \
                    height - height % 10
                    
    limit = np.min([width, height])

    step = np.linspace(0, limit - 1, limit)

    xv, yv = np.meshgrid(step, step)

    green = img_array[:limit, :limit, 1]



    fig, ax = plt.subplots()
    ax = plt.axes(projection='3d')

    ax.plot_surface(xv, yv, green, rstride = stride, cstride = stride, 
                    cmap = cm.coolwarm, linewidth = 0, antialiased = False)

    ax.w_xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0)) # Hide YZ Plane
    ax.w_yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0)) # Hide XZ Plane
    ax.grid(False)

    ax.set_zlabel('Pixel Intensity (au)')

    ax.get_xaxis().set_ticks([])
    ax.get_xaxis().line.set_linewidth(0)

    ax.get_yaxis().set_ticks([])
    ax.get_yaxis().line.set_linewidth(0)


def load_both(low_files, high_files):
    label_stats = ['low_mean_g', 'low_std_g', 'low_mean_r', 'low_std_r',
                   'high_mean_g', 'high_std_g', 'high_mean_r', 'high_std_r', ]
    
    label_max = ['low_max_g', 'low_max_r', 'high_max_g', 'high_max_r']
    
    stat_list = []
    max_list = []
    
    for low_file, high_file in tqdm(zip(low_files, high_files), total = len(low_files)):
        
        # get low file info
        jp2 = glymur.Jp2k(low_file)
        
        jp2_green = jp2[:, :, 1]
        jp2_red = jp2[:, :, 0]
        
        green_values = jp2_green[jp2_green > 0]
        red_values = jp2_red[jp2_red > 0]
        
        low_mean_g, low_std_g, low_max_g = np.mean(green_values), np.std(green_values), np.max(green_values)
        low_mean_r, low_std_r, low_max_r = np.mean(red_values), np.std(red_values), np.max(red_values)
        
        # get high file input
        jp2 = glymur.Jp2k(high_file)
        
        jp2_green = jp2[:, :, 1]
        jp2_red = jp2[:, :, 0]
        
        green_values = jp2_green[jp2_green > 0]
        red_values = jp2_red[jp2_red > 0]
        
        high_mean_g, high_std_g, high_max_g = np.mean(green_values), np.std(green_values), np.max(green_values)
        high_mean_r, high_std_r, high_max_r = np.mean(red_values), np.std(red_values), np.max(red_values)
        
        # save to list
        stat_list.append([low_mean_g, low_std_g, low_mean_r, low_std_r,
                          high_mean_g, high_std_g, high_mean_r, high_std_r])
        max_list.append([low_max_g, low_max_r, high_max_g, high_max_r])
    
    df1 = pd.DataFrame(stat_list, columns = label_stats, dtype = 'f2')
    df2 = pd.DataFrame(np.asarray(max_list).astype('i8'), columns = label_max, dtype = 'i8')
    
    return pd.concat([df1, df2], axis = 1)
    
    
def load_one(files):
    
    g_vals = []
    
    for file in tqdm(files, total = len(files)):
        
        # get low file info
        jp2 = glymur.Jp2k(file)        
        jp2_green = jp2[:, :, 1]
        
        g_vals.append(jp2_green[jp2_green > 0])

    return g_vals



#df = load_both(low_files, high_files)
#g_vals = load_one(low_files)
#download_jp2(jp2_input, jp2_output)

#df = load_both(low_files, high_files)
low_df = load_one(low_files)
#high_df = load_one(high_files)

plot_one(low_df, scales = [1])



