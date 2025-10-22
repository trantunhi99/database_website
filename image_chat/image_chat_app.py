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


TILE_CLIENT_REGISTRY = {}

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
    overlay_path = os.path.join(base_dir, sample_name, "raster_resized_overlay.tif")

    try:
        port = 9015

        # --- Base layer client ---
        if base_path in TILE_CLIENT_REGISTRY:
            base_client = TILE_CLIENT_REGISTRY[base_path]
            try:
                _ = base_client.center()
                print(f"♻️ Reusing base TileClient for {sample_name}")
            except Exception as e:
                print(f"⚠️ Cached base client invalid: {e}. Recreating.")
                base_client = None
        else:
            base_client = None

        if base_client is None:
            base_client = TileClient(
                base_path,
                cors_all=True,
                host="0.0.0.0",
                port=port,
                client_host="localhost",
                client_port=port,
            )
            TILE_CLIENT_REGISTRY[base_path] = base_client
            print(f"✅ New base TileClient created for {sample_name}")

        base_layer = get_leaflet_tile_layer(base_client)

        # --- Overlay layer client ---
        overlay_client = TileClient(
            overlay_path,
            cors_all=True,
            host="0.0.0.0",
            port=port - 1,  # use different port for overlay
            client_host="localhost",
            client_port=port - 1,
        )
        overlay_layer = get_leaflet_tile_layer(overlay_client)

        # --- Create leaflet map with both layers ---
        leaflet_map = create_leaflet_map(
            "map",
            base_client,
            base_layer,
            [(overlay_layer, "Overlay")],
        )

        return leaflet_map

    except Exception as e:
        print(f"❌ Failed to load image: {e}")
        return html.Div(f"Error loading image: {e}")


# ----------------------------------------------------------------------------
# ROI extraction (multi-user safe)
# ----------------------------------------------------------------------------
@app.callback(
    [Output("roi-data", "data"), Output("status5", "children")],
    Input("editControl", "geojson"),
    State("url", "href"),
    State("session-id", "data"),
    prevent_initial_call=True,
)
def extract_roi_from_draw(drawn_geojson, href, session_id):
    if not session_id:
        session_id = "default"
    print(f"🟢 ROI event triggered (session: {session_id})")

    query = parse_qs(urlparse(href).query)
    file_path = query.get("file", [None])[0]
    if not file_path:
        return {}, "❌ No file path found"

    parent = os.path.dirname(file_path)
    roi_dir = os.path.join(parent, "roi", session_id)
    os.makedirs(roi_dir, exist_ok=True)

    if not drawn_geojson or not drawn_geojson.get("features"):
        for f in glob.glob(os.path.join(roi_dir, "*.png")):
            os.remove(f)
        print(f"🗑️ Cleared all ROIs for session {session_id}")
        return {"paths": []}, f"🗑️ Cleared ROIs for session {session_id}"

    saved_paths = save_roi(drawn_geojson, file_path, output_dir=roi_dir, cleanup_old=True)
    print(f"✅ Session {session_id}: saved {len(saved_paths)} ROI(s).")
    return {"paths": saved_paths}, f"✅ {len(saved_paths)} ROI(s) saved (session {session_id})."


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
    app.run_server(host="0.0.0.0", port=8050, debug=False)
