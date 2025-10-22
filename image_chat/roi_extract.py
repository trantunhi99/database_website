
import copy
import json
import rasterio
import os
import cv2
import numpy as np

def get_coord_mapping(file_path):
        """Get coordinate mapping from geographic to pixel.
        
        Args:
            sample_id (str): sample id.
        
        Returns:
            func: coordinate mapping function.
        """
        raster = rasterio.open(
            file_path
        )
        return raster.index

def get_bounding_box(coords):
    """Get bounding box of coordinates.
    
    Args:
        coords (list of tuple): list of coordinates.
    
    Returns:
        tuple: bounding box.
    """
    x_coords, y_coords = zip(*coords)
    x1, y1 = min(x_coords), min(y_coords)
    x2, y2 = max(x_coords), max(y_coords)
    return x1, y1, x2, y2

def save_roi(drawn_geojson, file_path, output_dir=None, cleanup_old=False):
    """
    Process drawn ROI polygons and return list of cropped image paths.
    Supports session isolation (via output_dir) and layer separation (base vs cell_types).

    Args:
        drawn_geojson (dict): GeoJSON from EditControl.
        file_path (str): Full path to original image.
        output_dir (str, optional): Custom output directory for multi-user/session-safe saving.
        cleanup_old (bool): If True, delete stale ROIs before saving new ones.

    Returns:
        list[str]: Saved cropped image paths.
    """
    if not drawn_geojson or "features" not in drawn_geojson:
        print("⚠️ No ROI drawn.")
        return []

    # --- Setup paths ---
    mapper = get_coord_mapping(file_path)
    parent = os.path.dirname(file_path)

    # detect which layer we’re saving from
    if "overlay" in os.path.basename(file_path).lower():
        layer_type = "cell types"
    else:
        layer_type = "base layer"

    roi_path = output_dir or os.path.join(parent, "roi", layer_type)
    os.makedirs(roi_path, exist_ok=True)

    real_img_path = os.path.join(parent, "real_image", layer_type)
    if not os.path.isdir(real_img_path):
        # fallback to single real_image folder if layer-specific one doesn't exist
        real_img_path = os.path.join(parent, "real_image")

    if not os.path.isdir(real_img_path):
        raise FileNotFoundError(f"Missing folder: {real_img_path}")

    real_img_file = os.listdir(real_img_path)[0]
    real_image = cv2.imread(os.path.join(real_img_path, real_img_file))
    if real_image is None:
        raise ValueError("❌ Failed to read real image file")

    # --- Optionally clear old ROIs ---
    if cleanup_old:
        for f in os.listdir(roi_path):
            if f.startswith("roi_") and f.endswith(".png"):
                try:
                    os.remove(os.path.join(roi_path, f))
                    print(f"🗑️ Removed old ROI → {f}")
                except Exception:
                    pass

    # --- Save visible ROIs ---
    saved_paths = []
    for i, region in enumerate(drawn_geojson["features"]):
        coords = region["geometry"]["coordinates"][0]
        coords = [mapper(*p) for p in coords]
        coords = [[p[1], p[0]] for p in coords]  # flip to (x, y)
        x1, y1, x2, y2 = get_bounding_box(coords)

        cropped = copy.deepcopy(real_image)[y1:y2, x1:x2]
        coord_name = f"{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}"
        save_path = os.path.join(roi_path, f"roi_{i}_{coord_name}.png")

        cv2.imwrite(save_path, cropped)
        saved_paths.append(save_path)
        print(f"✅ ROI #{i+1} saved → {save_path}")

    return saved_paths





# from PIL import Image
# Image.MAX_IMAGE_PIXELS=None

# def save_roi(drawn_geojson, file_path, output_dir=None, cleanup_old=False):
#     """
#     Process drawn ROI polygons and return list of cropped image paths.
#     Uses Pillow (PIL) instead of OpenCV to avoid TIFF tile-size limit.

#     Args:
#         drawn_geojson (dict): GeoJSON from EditControl.
#         file_path (str): Full path to original image.
#         output_dir (str, optional): Custom output directory for multi-user/session-safe saving.
#         cleanup_old (bool): If True, delete stale ROIs before saving new ones.

#     Returns:
#         list[str]: Saved cropped image paths.
#     """
#     if not drawn_geojson or "features" not in drawn_geojson:
#         print("⚠️ No ROI drawn.")
#         return []

#     mapper = get_coord_mapping(file_path)
#     parent = os.path.dirname(file_path)
#     roi_path = output_dir or os.path.join(parent, "roi")
#     os.makedirs(roi_path, exist_ok=True)

#     real_img_path = os.path.join(parent, "real_image")
#     if not os.path.isdir(real_img_path):
#         raise FileNotFoundError(f"Missing folder: {real_img_path}")

#     real_img_file = os.listdir(real_img_path)[0]
#     real_image_path = os.path.join(real_img_path, real_img_file)

#     try:
#         # 🔥 Use Pillow — it streams tiles and avoids OpenCV limits
#         real_image = Image.open(real_image_path)
#         print(f"🖼️ Loaded with Pillow: {real_image.size}")
#     except Exception as e:
#         raise ValueError(f"❌ Failed to open real image file: {e}")

#     # Optional cleanup
#     if cleanup_old:
#         for f in os.listdir(roi_path):
#             if f.startswith("roi_") and f.endswith(".png"):
#                 try:
#                     os.remove(os.path.join(roi_path, f))
#                     print(f"🗑️ Removed old ROI → {f}")
#                 except Exception:
#                     pass

#     saved_paths = []
#     for i, region in enumerate(drawn_geojson["features"]):
#         coords = region["geometry"]["coordinates"][0]
#         coords = [mapper(*p) for p in coords]
#         #coords = [[p[1], p[0]] for p in coords]  # flip to (x, y)
#         x1, y1, x2, y2 = get_bounding_box(coords)

#         # 🔍 Crop directly from Pillow image
#         cropped = real_image.crop((x1, y1, x2, y2))
#         coord_name = f"{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}"
#         save_path = os.path.join(roi_path, f"roi_{i}_{coord_name}.png")

#         cropped.save(save_path, "PNG")
#         saved_paths.append(save_path)
#         print(f"✅ ROI #{i+1} saved → {save_path}")

#     return saved_paths
