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
from droplet_image_processing import process_images
from droplet_plotting import drop_plot
from csv_write import csv_writer

###############################################################################################################################################################
# Droplet counting script for use on the VAPPORIZING project: image processing to extract number of droplets per image area and distribution of droplet sizes #
############################################################################################################################################################### 

##########################################################################################################################################################
############################################################## GUI-BASED APPLET ##########################################################################
##########################################################################################################################################################

class DropletApp: 
    def __init__(self, root):
        self.root = root 
        root.geometry("1080x720")
        self.root.title("Droplet Counter") 
        self.folder_path = "" 
        tk.Label(root, text="Droplet Counter for VAPPORIZING Project", font=("Helvetica", 24, "bold", "underline")).pack(pady=10)
        tk.Label(root, text="Select a folder containing images to analyze and insert your diameter range for droplet detection. Then, run the analysis.", font=("Helvetica", 14), wraplength=500, justify="center").pack(pady=5)
        tk.Button(root, text="Select Image Folder", command=self.select_folder, width=20, height=2, bg="lightblue", font=("Helvetica", 12,"bold")).pack(pady=5)
        self.label = tk.Label(root, text="No folder selected", font=("Helvetica", 12, "italic"), fg="red") 
        self.label.pack() 
        tk.Label(root, text="Microns per pixel", font=("Helvetica", 12, "bold")).pack() 
        self.scale_entry = tk.Entry(root) 
        self.scale_entry.insert(0, "0.0925") 
        self.scale_entry.pack() 
        tk.Label(root, text="Min diameter (µm)", font=("Helvetica", 12, "bold")).pack() 
        self.min_entry = tk.Entry(root) 
        self.min_entry.insert(0, "2") 
        self.min_entry.pack() 
        tk.Label(root, text="Max diameter (µm)", font=("Helvetica", 12, "bold")).pack() 
        self.max_entry = tk.Entry(root) 
        self.max_entry.insert(0, "20") 
        self.max_entry.pack() 
        tk.Button(root, text="Run Analysis", command=self.run, width=20, height=2, bg="lightgreen", font=("Helvetica", 12, "bold")).pack(pady=10) 
        tk.Button(root, text="Exit", command=root.quit, width=12, height=2, bg="lightcoral", font=("Helvetica", 12, "bold")).pack(pady=5)
        # Frame to hold plots
        self.plot_frame = tk.Frame(root)
        self.plot_frame.pack(fill="both", expand=True)
        # Keep references to canvases
        self.canvases = []
    def select_folder(self): 
        self.folder_path = filedialog.askdirectory() 
        self.label.config(text=self.folder_path, font=("Helvetica", 12), fg="black")
    def run(self): 
        if not self.folder_path: 
            messagebox.showerror("Error", "Select a folder first") 
            return 
        try: 
            micron_per_pixel = float(self.scale_entry.get()) 
            min_diam = float(self.min_entry.get()) 
            max_diam = float(self.max_entry.get()) 
            # Area per image (35.52x19.98 micron capture area at specimen) according to 200x magnification and 1.85 µm/px sensor resolution
            # Total magnification = 10x base * 20x lens = 200x
            # 3840 px * 1.85 µm/px = 7104 µm sensor width
            # 2160 px * 1.85 µm/px = 3996 µm sensor height
            # 7104/200 = 35.52 µm capture area width at specimen
            # 3996/200 = 19.98 µm capture area height at specimen
            # 35.52 µm * 19.98 µm = 709.9296 µm² = 0.0007099296 mm² per image
            area_per_image_mm2 = 0.07097 # mm^2
            outfolderpathData = f"output/{self.folder_path.split('/')[-1]}/data"
            if not os.path.exists(outfolderpathData):
                os.makedirs(outfolderpathData)
            outfolderpathGraphs = f"output/{self.folder_path.split('/')[-1]}/graphs"
            if not os.path.exists(outfolderpathGraphs):
                os.makedirs(outfolderpathGraphs)
            diag_folder = os.path.join("output", os.path.basename(self.folder_path), "images")
            if not os.path.exists(diag_folder):
                os.makedirs(diag_folder)
            diameters, areas, avg_image, image_count = process_images(self.folder_path, micron_per_pixel, min_diam, max_diam, diag_folder)
            if len(diameters) == 0: 
                messagebox.showinfo("Result", "No droplets found") 
                return 
            self, diameters, areas, total_area_mm2, bins, outfolderpathGraphs = drop_plot(self, diameters, areas, image_count * area_per_image_mm2, np.arange(0, 25, 1), outfolderpathGraphs)
            # TOTAL AREA = number of images x image area (0.01774224 mm²)
            total_area_mm2 = image_count * area_per_image_mm2
            
            # DEBUG: Print statistics
            print(f"\n=== DEBUG INFO ===")
            print(f"Images processed: {image_count}")
            print(f"Total area: {total_area_mm2} mm²")
            print(f"Droplets detected: {len(diameters)}")
            print(f"Diameter stats - Min: {np.min(diameters):.2f}, Max: {np.max(diameters):.2f}, Mean: {np.mean(diameters):.2f}")
            print(f"Unique diameters: {len(np.unique(np.round(diameters, 1)))}")
            print(f"Total volume: {sum((1/6)*(math.pi)*(diameters*diameters*diameters)):.4f}")
            print(f"Average droplet volume: {sum((1/6)*(math.pi)*(diameters*diameters*diameters))/len(diameters):.4f}")
            print(f"=================\n")
            
            # Save data
            df = csv_writer(diameters, areas, outfolderpathData)
            # Remove old plots from the GUI before plotting new ones
            for canvas in self.canvases:
                canvas.get_tk_widget().destroy()
            self.canvases.clear()

            # Save average image 
            if avg_image is not None: 
                cv2.imwrite(os.path.join(outfolderpathGraphs, "average.png"), avg_image) 
            messagebox.showinfo("Done", f"Images processed: {image_count}\nTotal area: {total_area_mm2:.6f} mm²\n\nFiles saved successfully. \n\n Droplets detected: {len(diameters)}\nDiameter range: {np.min(diameters):.2f}-{np.max(diameters):.2f} µm\nAverage diameter: {np.mean(diameters):.2f} µm\nTotal volume: {sum((1/6)*(math.pi)*(diameters*diameters*diameters))}\nAverage droplet volume: {sum((1/6)*(math.pi)*(diameters*diameters*diameters))/len(diameters):.4f}\n") 

        except Exception as e: 
            messagebox.showerror("Error", str(e)) 

#########################################################################################################################################################
################################################################# GUI ###################################################################################
#########################################################################################################################################################

if __name__ == "__main__": 
    root = tk.Tk() 
    app = DropletApp(root) 
    root.mainloop() 
