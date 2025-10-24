import os
import random
import json
import glob
import uuid
import dash
import ollama
from flask import request, jsonify, send_file
from urllib.parse import urlparse, parse_qs
from dash import html, dcc, Input, Output, State
from localtileserver import TileClient, get_leaflet_tile_layer
from leaflet import create_leaflet_map
from roi_extract import save_roi
import urllib.parse
import numpy as np
# ----------------------------------------------------------------------------
# Dash setup
# ----------------------------------------------------------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# ----------------------------------------------------------------------------
# HTML shell
# ----------------------------------------------------------------------------
app.index_string = """
<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>Wang Lab — Image Viewer + Chatbot</title>
    {%favicon%}
    {%css%}
    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css" />
    <link rel="stylesheet" href="/assets/style.css" />
  </head>
  <body>
    {%app_entry%}
    <footer>© 2025 Wang Lab</footer>
    {%config%}
    {%scripts%}
    <script src="/assets/script.js"></script>
    {%renderer%}
  </body>
</html>
"""

# ----------------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------------
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),

    dcc.Store(id="roi-data"),
    html.Div(id="roi-data-mirror", style={"display": "none"}),

    dcc.Store(id="session-id"),
    html.Div(id="session-id-mirror", style={"display": "none"}),

    html.Header(html.H1("Wang Lab - Image Viewer & AI Chat")),
    html.Main(className="split-layout", children=[
        html.Div(className="image-panel", children=[
            html.H2("Image Visualization"),
            html.Div(id="map-container", children="Loading image..."),
            html.Div(id="status5", style={"fontSize": "12px", "color": "#666"}),
        ]),
        html.Div(className="chatbot-panel", children=[
            html.H2("AI Chatbot"),
            html.Div(id="chatMessages", className="chat-messages"),
            html.Div(className="chat-input", children=[
                dcc.Input(
                    id="chatInput",
                    type="text",
                    placeholder="Type your message...",
                    debounce=True,
                    autoComplete="off",
                    spellCheck=False,
                ),
                html.Button("Send", id="sendBtn"),
            ]),
        ]),
    ]),
])

# ----------------------------------------------------------------------------
# Session management
# ----------------------------------------------------------------------------
@app.callback(
    Output("session-id", "data"),
    Input("url", "href"),
    prevent_initial_call=False,
)
def create_session_id(_):
    sid = str(uuid.uuid4())[:8]
    print(f"🧠 Created session ID → {sid}")
    return sid


@app.callback(
    Output("session-id-mirror", "data-dash-store"),
    Input("session-id", "data"),
    prevent_initial_call=False,
)
def mirror_session_id_to_dom(session_id):
    payload = "{}" if not session_id else json.dumps({"session_id": session_id})
    print(f"🔁 Mirroring session ID to DOM: {payload}")
    return payload

# ----------------------------------------------------------------------------
# Image loading
# ----------------------------------------------------------------------------
# TILE_CLIENT_REGISTRY = {}

# @app.callback(
#     Output("map-container", "children"),
#     Input("url", "href"),
# )
# def load_image_from_url(href):
#     if not href:
#         return html.Div("No file specified in URL")

#     query = parse_qs(urlparse(href).query)
#     file_path = query.get("file", [None])[0]
#     if not file_path:
#         return html.Div("Missing ?file= parameter")

#     try:
#         port = 9015
#         client = None

#         if file_path in TILE_CLIENT_REGISTRY:
#             client = TILE_CLIENT_REGISTRY[file_path]
#             try:
#                 _ = client.center()
#                 print(f"♻️ Reusing TileClient for {file_path}")
#             except Exception as e:
#                 print(f"⚠️ Cached client invalid: {e}. Recreating.")
#                 client = None

#         if client is None:
#             client = TileClient(
#                 file_path,
#                 cors_all=True,
#                 host="0.0.0.0",
#                 port=port,
#                 client_host="localhost",
#                 client_port=port,
#             )
#             TILE_CLIENT_REGISTRY[file_path] = client
#             print(f"✅ New TileClient created for {file_path}")

#         layer = get_leaflet_tile_layer(client)
#         leaflet_map = create_leaflet_map("map", client, layer, [])
#         print(layer.url)
#         return leaflet_map

#     except Exception as e:
#         print(f"❌ Failed to load image: {e}")
#         return html.Div(f"Error loading image: {e}")


# Global registry

# TILE_CLIENT_REGISTRY = {}

# @app.callback(
#     Output("map-container", "children"),
#     Input("url", "href"),
# )
# def load_image_from_url(href):
#     if not href:
#         return html.Div("No sample specified in URL")

#     query = parse_qs(urlparse(href).query)
#     sample_name = query.get("file", [None])[0]
#     if not sample_name:
#         return html.Div("Missing ?file= parameter")

#     base_dir = "/condo/wanglab/shared/database"
#     base_path = os.path.join(base_dir, sample_name, "raster_resized.tif")
#     json_path = os.path.join(base_dir, sample_name, "present_cell_types.json")

#     # Folder containing overlay TIFFs
#     overlay_dir = os.path.join(base_dir, sample_name, "cell_types", "raster")

#     port = 9015
#     ip = "localhost"

#     try:
#         # --- Read JSON file with present cell types ---
#         if os.path.exists(json_path):
#             with open(json_path, "r") as f:
#                 classes = json.load(f)
#             print(f"🟢 Loaded {len(classes)} cell types from {json_path}")
#         else:
#             classes = []
#             print("⚠️ No present_cell_types.json found — classes set to empty list")

#         # --- Reuse or create base client ---
#         base_client = get_or_create_tile_client(base_path, ip, port)
#         base_layer = get_leaflet_tile_layer(base_client)

#         # --- Collect overlay layers ---
#         overlay_layers = []
#         if os.path.exists(overlay_dir):
#             for fname in os.listdir(overlay_dir):
#                 if fname.startswith("raster_") and fname.endswith(".tif"):
#                     overlay_path = os.path.join(overlay_dir, fname)
#                     # Extract celltype number
#                     layer_name = fname.split("celltype_")[-1].split(".tif")[0]
#                     layer_name = f"{layer_name}"
#                     try:
#                         overlay_client = get_or_create_tile_client(overlay_path, ip, port)
#                         overlay_layer = get_leaflet_tile_layer(overlay_client)
#                         overlay_layers.append((overlay_layer, layer_name))
#                         print(f"🟢 Added overlay layer: {layer_name}")
#                     except Exception as sub_e:
#                         print(f"⚠️ Failed to load {fname}: {sub_e}")
#         else:
#             print(f"⚠️ Overlay directory not found: {overlay_dir}")

#         # --- Create map with all overlay layers ---
#         leaflet_map = create_leaflet_map(
#             "map",
#             base_client,
#             base_layer,
#             overlay_layers,
#             classes=classes,
#             overlay=True
#         )
#         return leaflet_map

#     except Exception as e:
#         print(f"❌ Failed to load image: {e}")
#         return html.Div(f"Error loading image: {e}")


# def get_or_create_tile_client(file_path, ip, port):
#     """Reuses or creates a TileClient, with validation and registry tracking."""
#     if file_path in TILE_CLIENT_REGISTRY:
#         info = TILE_CLIENT_REGISTRY[file_path]
#         client = info["client"]
#         info["count"] += 1
#         try:
#             _ = client.center()
#             print(f"♻️ Reusing valid TileClient for {file_path}")
#             return client
#         except Exception as e:
#             print(f"⚠️ Client invalid ({e}), recreating...")
#     client = TileClient(file_path, cors_all=True, host="0.0.0.0", port=port, client_host=ip, client_port=port)
#     TILE_CLIENT_REGISTRY[file_path] = {"client": client, "port": port, "count": 1}
#     print(f"✅ Created new TileClient on {ip}:{port} for {file_path}")
#     return client


import os, json
from urllib.parse import urlparse, parse_qs
from dash import html, Input, Output
from tileclient import TileClient, get_leaflet_tile_layer

TILE_CLIENT_REGISTRY = {}

# --- consistent color dictionary ---
COLOR_DICT_CELLS = {
    1: [255, 0, 0],        # Neoplastic
    2: [34, 221, 77],      # Immune
    3: [35, 92, 236],      # Stromal
    4: [255, 209, 102],    # Epithelial
    5: [255, 159, 68],     # Fibroblast
    6: [200, 50, 50],      # Endothelial
    7: [60, 40, 120],      # Cardiomyocyte
    8: [35, 192, 236],     # Cardiac Fibroblast
    9: [254, 255, 100],    # Smooth Muscle
    10: [153, 102, 255],   # Adipose
    11: [255, 159, 168],   # Oligodendrocyte
    12: [255, 59, 68],     # Astrocyte
    13: [92, 200, 186],    # Neuron
    14: [255, 0, 100],     # Vascular Smooth Muscle
    15: [34, 221, 177],    # Alveolar pneumocytes
    16: [35, 92, 136],     # Chondrocytes
    17: [254, 55, 0],      # Hepatocyte
    18: [120, 68, 229],    # Glia
    19: [68, 133, 229],    # Pericentral hepatocytes
    20: [120, 229, 68],    # Proliferating keratinocytes
    21: [0, 180, 229],     # Spinous keratinocytes
    22: [120, 0, 68],      # Connective
    23: [229, 180, 68],    # Lamina propria
    24: [229, 68, 180],    # Reserved / extra
    25: [68, 229, 120],    # Reserved / extra
}


@app.callback(
    Output("map-container", "children"),
    Input("url", "href"),
)
def load_image_from_url(href):
    if not href:
        return html.Div("No sample specified in URL")

    query = parse_qs(urlparse(href).query)
    sample_name = query.get("file", [None])[0]
    if not sample_name:
        return html.Div("Missing ?file= parameter")

    base_dir = "/condo/wanglab/shared/database"
    base_path = os.path.join(base_dir, sample_name, "raster_resized.tif")
    json_path = os.path.join(base_dir, sample_name, "present_cell_types.json")

    # folder containing grayscale mask overlays
    overlay_dir = os.path.join(base_dir, sample_name, "cell_types", "raster")

    port = 9015
    ip = "localhost"

    try:
        # --- load class list ---
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                classes = json.load(f)
            print(f"🟢 Loaded {len(classes)} cell types from {json_path}")
        else:
            classes = []
            print("⚠️ No present_cell_types.json found — empty list")

        # --- base layer ---
        base_client = get_or_create_tile_client(base_path, ip, port)
        base_layer = get_leaflet_tile_layer(base_client)

        # --- overlay layers (1-channel masks) ---
        overlay_layers = []
        if os.path.exists(overlay_dir):
            for fname in os.listdir(overlay_dir):
                if not fname.startswith("raster_") or not fname.endswith(".tif"):
                    continue

                overlay_path = os.path.join(overlay_dir, fname)
                # extract celltype name (keep exact filename rule)
                layer_name = fname.split("celltype_")[-1].split(".tif")[0]

                # parse numeric ID if available
                try:
                    ctype_id = int(layer_name)
                except ValueError:
                    ctype_id = None

                # determine color (by numeric ID or fallback)
                if ctype_id is not None and ctype_id in COLOR_DICT_CELLS:
                    color = COLOR_DICT_CELLS[ctype_id]
                else:
                    # fallback: hash to stable random color
                    np.random.seed(abs(hash(layer_name)) % (2**32))
                    color = np.random.randint(0, 255, 3).tolist()

                try:
                    overlay_client = get_or_create_tile_client(overlay_path, ip, port)

                    # apply runtime colorization for 1-channel mask
                    overlay_layer = get_leaflet_tile_layer(
                        overlay_client,
                        colormap=[[0, 0, 0, 0], color + [220]],  # transparent background + color
                        vmin=0,
                        vmax=255,
                        nodata=0,
                    )
                    overlay_layers.append((overlay_layer, layer_name))
                    print(f"🟢 Added {layer_name} with color {color}")

                except Exception as sub_e:
                    print(f"⚠️ Failed to load {fname}: {sub_e}")
        else:
            print(f"⚠️ Overlay directory not found: {overlay_dir}")

        # --- build map ---
        leaflet_map = create_leaflet_map(
            "map",
            base_client,
            base_layer,
            overlay_layers,
            classes=classes,
            overlay=True
        )
        return leaflet_map

    except Exception as e:
        print(f"❌ Failed to load image: {e}")
        return html.Div(f"Error loading image: {e}")


def get_or_create_tile_client(file_path, ip, port):
    """Reuse or create a TileClient with caching."""
    if file_path in TILE_CLIENT_REGISTRY:
        info = TILE_CLIENT_REGISTRY[file_path]
        client = info["client"]
        try:
            _ = client.center()
            print(f"♻️ Reusing TileClient for {file_path}")
            return client
        except Exception:
            print(f"⚠️ Recreating TileClient for {file_path}")
    client = TileClient(
        file_path,
        cors_all=True,
        host="0.0.0.0",
        port=port,
        client_host=ip,
        client_port=port,
    )
    TILE_CLIENT_REGISTRY[file_path] = {"client": client, "port": port}
    print(f"✅ Created new TileClient for {file_path}")
    return client


# ----------------------------------------------------------------------------
# ROI extraction (multi-user safe)
# ----------------------------------------------------------------------------
import os
import glob
import json
from urllib.parse import urlparse, parse_qs

from dash import Output, Input, State, html


@app.callback(
    [Output("roi-data", "data"), Output("status5", "children")],
    Input("editControl", "geojson"),            # User drawing input
    Input("layer-overlay", "baseLayer"),        # Active base layer
    Input("layer-overlay", "overlays"),          # Active overlay
    State("url", "href"),                       # URL to get sample name
    State("session-id", "data"),                # Session handling
    prevent_initial_call=True,
)
def extract_roi_from_draw(drawn_geojson, base_layer, overlay, href, session_id):
    # --- Handle session ---
    if not session_id:
        session_id = "default"
    print(f"🟢 ROI event triggered (session: {session_id})")

    # --- Parse URL and sample name ---
    query = parse_qs(urlparse(href).query)
    sample_name = query.get("file", [None])[0]
    if not sample_name:
        return {}, "❌ Missing ?file= parameter"

    # --- Define paths ---
    base_dir = "/condo/wanglab/shared/database"
    base_path = os.path.join(base_dir, sample_name, "raster_resized.tif")
    overlay_path = os.path.join(base_dir, sample_name, "raster_resized_overlay.tif")
    # print(overlay)

    # --- Determine which layer the user drew on ---
    # overlay = name of the active overlay (None if none selected)
    if overlay and len(overlay) > 0:
        layer_type = "cell_types"
        file_path = overlay_path
    else:
        layer_type = "base_layer"
        file_path = base_path

    print(f"🧭 Active layer type: {layer_type} (base_layer={base_layer}, overlay={overlay})")

    # --- Build proper ROI directory ---
    parent = os.path.dirname(file_path)
    roi_dir = os.path.join(parent, "roi", layer_type, session_id)
    os.makedirs(roi_dir, exist_ok=True)

    # --- Handle "no drawing" (clear all) ---
    if not drawn_geojson or not drawn_geojson.get("features"):
        removed_files = 0
        for f in glob.glob(os.path.join(roi_dir, "*.png")):
            os.remove(f)
            removed_files += 1
        print(f"🗑️ Cleared {removed_files} ROI(s) for session {session_id} ({layer_type})")
        return {"paths": []}, f"🗑️ Cleared ROIs for {layer_type} (session {session_id})"

    # --- Save new ROIs ---
    try:
        saved_paths = save_roi(
            drawn_geojson,
            file_path,
            output_dir=roi_dir,
            cleanup_old=True,
        )
        print(f"✅ Session {session_id} ({layer_type}): saved {len(saved_paths)} ROI(s).")
        return {"paths": saved_paths}, f"✅ {len(saved_paths)} ROI(s) saved ({layer_type}, session {session_id})."
    except Exception as e:
        print(f"❌ ROI save failed: {e}")
        return {}, f"❌ Failed to save ROIs: {e}"






@app.callback(
    Output("roi-data-mirror", "data-dash-store"),
    Input("roi-data", "data"),
    prevent_initial_call=True,
)
def sync_store_to_dom(roi_data):
    try:
        json_str = "{}" if not roi_data else json.dumps(roi_data)
        print(f"🔁 Mirroring ROI data to DOM: {json_str}")
        return json_str
    except Exception as e:
        print(f"⚠️ Mirror update failed: {e}")
        return "{}"


@app.callback(
    Output("chatInput", "value"),
    [Input("sendBtn", "n_clicks"), Input("chatInput", "n_submit")],
    prevent_initial_call=True,
)
def clear_after_send(_, __):
    return ""

# ----------------------------------------------------------------------------
# Chat history helpers
# ----------------------------------------------------------------------------
CHAT_HISTORY_DIR = "./chat_sessions"
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

def load_history(session_id: str):
    path = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load history for {session_id}: {e}")
    return []

def save_history(session_id: str, history):
    path = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
    try:
        with open(path, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save history for {session_id}: {e}")

def clean_history_images(history):
    """Remove old or missing ROI image references from previous messages."""
    for i, msg in enumerate(history):
        # remove all 'images' from any previous message (only current allowed)
        if "images" in msg:
            if i < len(history) - 1:
                print(f"🧹 Removed images from older message {i}")
                msg.pop("images", None)
            elif isinstance(msg["images"], list):
                # keep only valid existing paths in the *last* one if needed
                valid = [p for p in msg["images"] if os.path.exists(p)]
                if len(valid) != len(msg["images"]):
                    print(f"⚠️ Cleaned invalid paths in last message: {msg['images']}")
                msg["images"] = valid
    return history

# ----------------------------------------------------------------------------
# Ollama Vision (persistent chat via JSON)
# ----------------------------------------------------------------------------
def ollama_vision_generate(
    model: str,
    prompt: str,
    images=None,
    session_id: str = "default",
    ollama_host: str = "http://localhost:11434",
):
    os.environ["OLLAMA_HOST"] = ollama_host
    client = ollama.Client()

    if isinstance(images, str):
        images = [images]
    elif images is None:
        images = []

    # load + clean history
    history = clean_history_images(load_history(session_id))

    # append new message with current ROI
    new_images = [p for p in images if os.path.exists(p)]
    history.append({"role": "user", "content": prompt, "images": new_images})

    try:
        print(f"📡 Querying Ollama model ({model}) via {ollama_host} [session={session_id}]")
        response = client.chat(model=model, messages=history)
        reply = response["message"]["content"].strip()
        history.append({"role": "assistant", "content": reply})
        save_history(session_id, history)
        print(f"🧠 Model response → {reply[:120]}...")
        return reply

    except Exception as e:
        print(f"❌ Model offline or unreachable: {e}")
        roi_info = (
            "No ROI images attached."
            if not new_images
            else "\n• " + "\n• ".join(os.path.basename(p) for p in new_images)
        )
        mock_reply = f"(Offline mode) '{prompt[:50]}...'\nImages:{roi_info}"
        history.append({"role": "assistant", "content": mock_reply})
        save_history(session_id, history)
        print(f"🧪 Mock response:\n{mock_reply}")
        return mock_reply

# ----------------------------------------------------------------------------
# REST endpoint → JS calls this
# ----------------------------------------------------------------------------
@server.route("/api/chat", methods=["POST"])
def chat_api():
    try:
        data = request.get_json(force=True)
        model = data.get("model", "qwen2.5vl:72b")
        prompt = data.get("prompt", "")
        images = data.get("images", [])
        session_id = data.get("session_id", "default")

        print(f"💬 Incoming chat:\n - Model: {model}\n - Session: {session_id}\n - Prompt: {prompt}\n - Images: {images}")
        reply = ollama_vision_generate(model=model, prompt=prompt, images=images, session_id=session_id)
        return jsonify({"response": reply})
    except Exception as e:
        print(f"❌ Chat API error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------------------------
# Optional route: Clear chat
# ----------------------------------------------------------------------------
@server.route("/api/reset_chat", methods=["POST"])
def reset_chat():
    try:
        data = request.get_json(force=True)
        session_id = data.get("session_id", "default")
        path = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑️ Cleared chat for {session_id}")
        return jsonify({"status": "cleared"})
    except Exception as e:
        print(f"❌ Reset chat error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------------------------
# Image preview route
# ----------------------------------------------------------------------------
@server.route("/preview")
def preview_image():
    path = request.args.get("path")
    if not path:
        return "Missing path", 400
    path = urllib.parse.unquote(path)
    if not os.path.exists(path):
        print(f"❌ Image not found: {path}")
        return f"Not found: {path}", 404
    print(f"🖼️ Serving preview: {path}")
    return send_file(path, mimetype="image/png")

# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Dash app running on http://0.0.0.0:8050")
    print("🧠 Using HPC Ollama via SSH tunnel → localhost:11434")
    app.run_server(host="0.0.0.0", port=8050, debug=True)
