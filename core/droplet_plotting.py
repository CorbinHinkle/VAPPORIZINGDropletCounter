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

def drop_plot(self, diameters, areas, total_area_mm2, volume, volume_fraction, bins, outfolderpathGraphs):
            counts, edges = np.histogram(diameters, bins=bins)
            counts_per_area = counts / total_area_mm2
            
                # DEBUG: Show histogram details
            non_zero_bins = np.where(counts > 0)[0]
            print(f"\nHistogram bins with droplets:")
            for idx in non_zero_bins:
                print(f"  Bin {idx}: {edges[idx]:.2f}-{edges[idx+1]:.2f} µm → {counts[idx]} droplets → {counts_per_area[idx]:.1f} per mm²")
            fig1 = Figure(figsize=(3,2), dpi=100)
            ax1 = fig1.add_subplot(111)

            ax1.bar(edges[:-1],
                    counts_per_area,
                    width=np.diff(edges),
                    align='edge')

            ax1.set_xlabel("Diameter (µm)")
            ax1.set_ylabel("Count per mm²")
            ax1.set_title("Droplet Distribution")

            canvas1 = FigureCanvasTkAgg(fig1, master=self.plot_frame)
            canvas1.draw()
            canvas1.get_tk_widget().grid(row=0, column=0, padx=10, pady=10)

            self.canvases.append(canvas1)

            fig1.savefig(os.path.join(outfolderpathGraphs, "count_per_area.png"))

            # ------------------------- 
            # Plot 2: Area-weighted distribution 
            # ------------------------- 

            area_sum_per_bin = np.zeros(len(edges) - 1) 
            for i in range(len(edges) - 1): 
                mask = (diameters >= edges[i]) & (diameters < edges[i+1]) 
                area_sum_per_bin[i] = np.sum(areas[mask]) 

            # Normalize by total area (OPTIONAL but better scientifically) 
            area_fraction = area_sum_per_bin / (total_area_mm2 * 1e6)  # µm² → mm² 

            fig2 = Figure(figsize=(3,2), dpi=100)
            ax2 = fig2.add_subplot(111)

            ax2.bar(edges[:-1], area_fraction, width=np.diff(edges),align='edge')

            ax2.set_xlabel("Diameter (µm)")
            ax2.set_ylabel("Area Fraction")
            ax2.set_title("Area-Weighted Distribution")

            canvas2 = FigureCanvasTkAgg(fig2, master=self.plot_frame)
            canvas2.draw()
            canvas2.get_tk_widget().grid(row=0, column=1, padx=10, pady=10)

            self.canvases.append(canvas2)

            fig2.savefig(os.path.join(outfolderpathGraphs, "area_fraction.png"))

            # ------------------------- 
            # Plot 3: Teflon-scaled count per area
            # ------------------------- 
            
            teflon_area = (1/4)*(math.pi)*(20**2) # Area of teflon plate onto which droplets are nebulized
            counts_per_teflon = counts_per_area*teflon_area # Droplet count per area scaled for teflon plate
            fig3 = Figure(figsize=(3,2), dpi=100)
            ax3 = fig3.add_subplot(111)

            ax3.bar(edges[:-1], counts_per_teflon, width=np.diff(edges), align='edge')

            ax3.set_xlabel("Diameter (µm)")
            ax3.set_ylabel("Count per mm²")
            ax3.set_title(f"Droplet Distribution (#/mm²)\nTotal Teflon Plate Area = {teflon_area:.6f} mm²")

            canvas3 = FigureCanvasTkAgg(fig3, master=self.plot_frame)
            canvas3.draw()
            canvas3.get_tk_widget().grid(row=0, column=2, padx=10, pady=10)

            self.canvases.append(canvas3)

            fig3.savefig(os.path.join(outfolderpathGraphs, "count_per_teflon.png"))

            volume = ((1/6)*(math.pi)*(diameters*diameters*diameters))/10000  # Volume of each droplet in cm³
            volume_sum_per_bin = np.zeros(len(edges) - 1)
            for i in range(len(edges) - 1):
                mask = (diameters >= edges[i]) & (diameters < edges[i+1])
                volume_sum_per_bin[i] = np.sum(volume[mask])
            volume_fraction = volume_sum_per_bin / (total_area_mm2 * 1e6)  # µm² → mm² 
                    
            fig4 = Figure(figsize=(5,4), dpi=100)
            ax4 = fig4.add_subplot(111)
            ax4.bar(edges[:-1], volume_fraction, width=np.diff(edges),align='edge')
            ax4.set_xlabel("Diameter (µm)")
            ax4.set_ylabel("Volume Fraction")
            ax4.set_title("Volume-Weighted Distribution")
            canvas4 = FigureCanvasTkAgg(fig4, master=self.plot_frame)
            canvas4.draw()
            canvas4.get_tk_widget().grid(row=0, column=3, padx=8, pady=8)
            self.canvases.append(canvas4)
            fig4.savefig(os.path.join(outfolderpathGraphs, "volume_distribution.png"))
            
            return self, diameters, areas, total_area_mm2, volume, volume_fraction, bins, outfolderpathGraphs

            