import os
import shutil 
import cv2 
import numpy as np 
import math
import pandas as pd 
import tkinter as tk 
from tkinter import filedialog, messagebox, ttk
from skimage import measure 
import matplotlib.pyplot as plt 
from skimage.feature import blob_log
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

###############################################################################################################################################################
# Droplet counting script for use on the VAPPORIZING project: image processing to extract number of droplets per image area and distribution of droplet sizes #
############################################################################################################################################################### 

def process_images(folder, micron_per_pixel, min_diam, max_diam, diag_folder): 
    # List initialization 
    diameters = [] 
    areas = []
    image_stack = [] 
    base_shape = None 
    image_count = 0

            #################################################################################################################################################
            ######################################################## IMAGE & FOLDER LOADING #################################################################
            #################################################################################################################################################

    for filename in os.listdir(folder): 
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")): 
            path = os.path.join(folder, filename) 
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE) 
            if img is None: 
                continue 
            image_count += 1 
            # Resize consistency 
            if base_shape is None: 
                base_shape = img.shape 
            else: 
                if img.shape != base_shape: 
                    img = cv2.resize(img, (base_shape[1], base_shape[0])) 
            image_stack.append(img) 

            ####################################################################################################################################################
            ######################### IMAGE PROCESSING STEPS (w/ enhanced diagnostics and adjustments for small droplet detection) #############################
            ####################################################################################################################################################

            # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=1.25, tileGridSize=(32,32))
            enhanced = clahe.apply(img)
            # Gaussian blurring to reduce noise and create a smooth background for subtraction (helps with uneven illumination)
            #background = cv2.GaussianBlur(enhanced, (51, 51), 0)
            # Subtract background
            #corrected = cv2.subtract(enhanced, background)
            # Thresholding for illumination correction 
            thresh = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 101, 1) 
            # Remove edge artifacts by creating a larger border mask
            h, w = enhanced.shape
            border_mask = np.ones_like(enhanced, dtype=np.uint8) * 255
            border_size = 5  # Reduced from 20 to 5 - minimal border removal
            border_mask[:border_size, :] = 0
            border_mask[-border_size:, :] = 0
            border_mask[:, :border_size] = 0
            border_mask[:, -border_size:] = 0
            thresh = cv2.bitwise_and(thresh, border_mask)
            # More aggressive morphological operations to remove noise
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1) 
            from scipy import ndimage as ndi
            thresh = ndi.binary_fill_holes(thresh > 0).astype(np.uint8) * 255 
            # Removed MORPH_CLOSE to avoid merging fragments
            labels = measure.label(thresh) 
            # Extract properties of labeled regions using the corrected image for intensity-based measurements (if needed for future enhancements)
            # Analyze connected components
            props = measure.regionprops(labels)
            # Convert grayscale image to color for diagnostics
            img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            ###########################################################################################################################################################
            ############################################################# IMAGE ANALYSIS & FILTERING ##################################################################
            ###########################################################################################################################################################

            # Initialize diagnostic images
            all_objects_img = img_color.copy()
            accepted_img = img_color.copy()

            # Per-image counter initialization
            droplets_in_image = 0
            rejected_size_small = 0
            rejected_size_large = 0
            rejected_circularity = 0
            rejected_range = 0
            image_diameters = []
############# IMAGE SCANNING LOOP ############################################################################################################################################################
            for prop in props:
                area_px = prop.area
                # Reject tiny objects
                if area_px < 100:
                    rejected_size_small += 1
                    continue
                # Reject huge objects
                if area_px > 150000:
                    rejected_size_large += 1
                    continue
                # Area extraction from centroid
                cy, cx = map(int, prop.centroid)
                radius = max(1, int(np.sqrt(area_px / np.pi)))
                # Draw all candidate objects (blue)
                cv2.circle(all_objects_img, (cx, cy), radius, (255, 0, 0), 1)
                # Circularity filtering based on area and perimeter (Crofton method is more robust for small objects)
                perimeter = prop.perimeter_crofton
                if perimeter <= 0:
                    rejected_circularity += 1
                    continue
                circularity = 4 * np.pi * area_px / perimeter**2
                if circularity < 0.10:
                    rejected_circularity += 1
                    continue
                # Calculate equivalent diameter
                diameter_px = np.sqrt(4 * area_px / np.pi)
                diameter_um = diameter_px * micron_per_pixel
                # User-defined diameter range filtering
                if not (min_diam <= diameter_um <= max_diam):
                    rejected_range += 1
                    continue
                area_um2 = area_px * micron_per_pixel**2
                image_diameters.append(diameter_um)
                diameters.append(diameter_um)
                areas.append(area_um2)
                droplets_in_image += 1
                # Draw accepted droplets (green)
                cv2.circle(accepted_img, (cx, cy), radius, (0, 255, 0), 2)
            # Print diagnostics per image
            if image_diameters:
                print(f"Image {image_count}: " f"{droplets_in_image} droplets passed in range | " f"{rejected_range} droplets outside diameter range | " f"{rejected_size_small} artifacts too small in area | " f"{rejected_size_large} artifacts too large in area | " f"{rejected_circularity} non-circular artifacts")
                print(f"  Diameter range: " f"{min(image_diameters):.3f}–{max(image_diameters):.3f} µm")
            else:
                print(f"Image {image_count}: " f"0 droplets passed in range | " f"{rejected_range} droplets outside diameter range | " f"{rejected_size_small} artifacts too small in area | " f"{rejected_size_large} artifacts too large in area | " f"{rejected_circularity} non-circular artifacts")

            # Save diagnostic images
            cv2.imwrite(os.path.join(diag_folder, f"image_{image_count}_all_objects.png"), all_objects_img)
            cv2.imwrite(os.path.join(diag_folder, f"image_{image_count}_accepted_droplets.png"), accepted_img)
            cv2.imwrite(os.path.join(diag_folder, f"image_{image_count}_enhanced.png"), enhanced)
            cv2.imwrite(os.path.join(diag_folder, f"image_{image_count}_threshold.png"), thresh)
############################################################################################################################################################################################################################################

    # Average image initialization
    avg_image = None 

    if len(image_stack) > 0: 
        avg_image = np.mean(image_stack, axis=0).astype(np.uint8) 
    return np.array(diameters), np.array(areas), avg_image, image_count 
