"""
create_icon.py — Generate assets/app_icon.ico programmatically.

Converts the provided logo.jpg into a multi-size .ico file.
"""

import os
from PIL import Image

def create_icon():
    sizes = [256, 128, 64, 48, 32, 16]
    
    os.makedirs("assets", exist_ok=True)
    
    try:
        img = Image.open("assets/logo.jpg")
        
        # Ensure it has an alpha channel for transparent background if any,
        # but since it's a jpeg, it's RGB. Convert to RGBA just in case.
        img = img.convert("RGBA")
        
        # Resize to largest size first
        base_img = img.resize((sizes[0], sizes[0]), Image.Resampling.LANCZOS)
        
        frames = []
        for size in sizes:
            resized = base_img.resize((size, size), Image.Resampling.LANCZOS)
            frames.append(resized)
            
        frames[0].save(
            "assets/app_icon.ico",
            format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=frames[1:]
        )
        print(f"Icon saved to assets/app_icon.ico ({len(sizes)} sizes)")
    except Exception as e:
        print(f"Error creating icon: {e}")

if __name__ == "__main__":
    create_icon()
