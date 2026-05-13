import h5py
import tkinter as tk
from tkinter import filedialog

def select_file():
    # Hide the root tkinter window
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Select an HDF5 file",
        filetypes=[("HDF5 files", "*.h5 *.hdf5"), ("All files", "*.*")]
    )
    
    return file_path

def print_h5_structure(file_path):
    def recurse(name, obj):
        depth = name.count('/')
        indent = "  " * depth
        
        if isinstance(obj, h5py.Group):
            print(f"{indent}[Group] {name}")
        
        elif isinstance(obj, h5py.Dataset):
            print(f"{indent}[Dataset] {name}")
            print(f"{indent}  Shape: {obj.shape}")
            print(f"{indent}  Dtype: {obj.dtype}")
            
            # Dataset size
            size_mb = obj.size * obj.dtype.itemsize / (1024**2)
            print(f"{indent}  Size: {size_mb:.2f} MB")
            
            # Attributes
            if obj.attrs:
                print(f"{indent}  Attributes:")
                for key, val in obj.attrs.items():
                    print(f"{indent}    - {key}: {val}")

    with h5py.File(file_path, "r") as f:
        print(f"\nHDF5 Structure: {file_path}\n")
        f.visititems(recurse)

if __name__ == "__main__":
    file_path = select_file()
    
    if file_path:
        print_h5_structure(file_path)
    else:
        print("No file selected.")