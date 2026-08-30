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

def csv_writer(diameters, areas, outfolderpathData):
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
    return df