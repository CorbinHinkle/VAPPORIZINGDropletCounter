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
                if area_px < 10:
                    rejected_size_small += 1
                    continue
                # Reject huge objects
                if area_px > 15000000:
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
            df = pd.DataFrame({"Droplet Diameter (um)": diameters, "Droplet Area (um2)": areas, "Droplet Volume (um3)": (1/6)*(math.pi)*(diameters*diameters*diameters)})
            
            # Remove old CSV file if it exists (fixes permission denied errors on Windows)
            csv_path = os.path.join(outfolderpathData, "droplet_results.csv")
            if os.path.exists(csv_path):
                try:
                    os.remove(csv_path)
                except Exception as e:
                    messagebox.showwarning("Warning", f"Could not remove old file: {e}\nIt may be open in another program.")
                    return
            
            df.to_csv(csv_path, index=False) 
            
            # Remove old plots from the GUI before plotting new ones
            for canvas in self.canvases:
                canvas.get_tk_widget().destroy()
            self.canvases.clear()

            ####################################################################################################################
            ############################################## PLOTTING ############################################################
            ####################################################################################################################
            
            # ------------------------- 
            # Plot 1: Count per area 
            # ------------------------- 
            # Adaptive binning: Use fewer bins for small sample sizes
            bins = max(5, min(30, len(diameters) // 2000)) if len(diameters) > 0 else 10
            print(f"Using {bins} bins for {len(diameters)} droplets")

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
            
            teflon_area = (1/4)*(math.pi)*(100**2) # Area of teflon plate onto which droplets are nebulized
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