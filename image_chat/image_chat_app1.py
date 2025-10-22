import os
import random
import json
import glob
import uuid
import dash
import ollama
from flask import request, jsonify
from urllib.parse import urlparse, parse_qs
from dash import html, dcc, Input, Output, State
from localtileserver import TileClient, get_leaflet_tile_layer
from leaflet import create_leaflet_map
#from niceview.pyplot.leaflet import create_leaflet_map
from roi_extract import save_roi

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
    dcc.Store(id="session-id"),  # ✅ stable session folder
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
# Create a persistent session ID per browser tab
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

# ----------------------------------------------------------------------------
# Image loading
# ----------------------------------------------------------------------------
TILE_CLIENT_REGISTRY = {}

@app.callback(
    Output("map-container", "children"),
    Input("url", "href"),
)


def load_image_from_url(href):
    if not href:
        return html.Div("No file specified in URL")

    query = parse_qs(urlparse(href).query)
    file_path = query.get("file", [None])[0]
    if not file_path:
        return html.Div("Missing ?file= parameter")

    # Reuse or create a TileClient
    try:
        port = 9015
        client = None

        # ✅ Check cache
        if file_path in TILE_CLIENT_REGISTRY:
            client = TILE_CLIENT_REGISTRY[file_path]
            try:
                # sanity check: ensure client still works
                _ = client.center()
                print(f"♻️ Reusing TileClient for {file_path}")
            except Exception as e:
                print(f"⚠️ Cached client invalid: {e}. Recreating.")
                client = None

        # ❌ If not cached, create a new one
        if client is None:
            client = TileClient(
                file_path,
                cors_all=True,
                host="0.0.0.0",
                port=port,
                client_host="localhost",
                client_port=port,
            )
            TILE_CLIENT_REGISTRY[file_path] = client
            print(f"✅ New TileClient created for {file_path}")

        # Generate map
        layer = get_leaflet_tile_layer(client)
        leaflet_map = create_leaflet_map("map", client, layer, [])
        print(layer.url)
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

    # Handle "delete all" (no features left)
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
    """
    When the Store updates, mirror it into a visible DOM attribute so JS can read it.
    """
    try:
        if roi_data:
            json_str = json.dumps(roi_data)
            print(f"🔁 Mirroring ROI data to DOM: {json_str}")
            return json_str
        return "{}"
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
# Ollama Vision (with mock fallback)
# ----------------------------------------------------------------------------
def ollama_vision_generate(
    model: str,
    prompt: str,
    images=None,
    ollama_host: str = "http://localhost:11434",
):
    os.environ["OLLAMA_HOST"] = ollama_host
    client = ollama.Client()

    if isinstance(images, str):
        images = [images]
    elif images is None:
        images = []

    messages = [{"role": "user", "content": prompt, "images": images}]

    try:
        print(f"📡 Querying Ollama model ({model}) via {ollama_host}")
        response = client.chat(model=model, messages=messages)
        reply = response["message"]["content"].strip()
        print(f"🧠 Model response → {reply[:120]}...")
        return reply

    except Exception as e:
        print(f"❌ Model offline or unreachable: {e}")

        # --- Format ROI details ---
        if images:
            # Extract short names and coords
            roi_descriptions = []
            for img_path in images:
                filename = os.path.basename(img_path)
                coord_hint = ""
                # Try to extract coords from filename pattern: roi_X_x1_y1_x2_y2.png
                parts = filename.split("_")
                if len(parts) >= 6 and parts[-1].endswith(".png"):
                    coord_hint = f"({parts[-5]},{parts[-4]})–({parts[-3]},{parts[-2]})"
                roi_descriptions.append(f"{filename} {coord_hint}".strip())
            roi_info = "\n• " + "\n• ".join(roi_descriptions)
        else:
            roi_info = "No ROI images attached."

        # --- Mocked responses ---
        mock_replies = [
            f"(Simulated) ROI processed for '{prompt[:40]}...'.\nAttached ROIs:{roi_info}",
            f"(Mock) Model offline. Would analyze:\nPrompt: '{prompt[:60]}...'\nImages:{roi_info}",
            f"(Offline Mode) Received input '{prompt[:35]}...'\nImage Context:{roi_info}\nMock inference complete.",
        ]

        mock_choice = random.choice(mock_replies)
        print(f"🧪 Mock response:\n{mock_choice}")
        return mock_choice


# ----------------------------------------------------------------------------
# REST endpoint → JS calls this
# ----------------------------------------------------------------------------
@server.route("/api/chat", methods=["POST"])
def chat_api():
    try:
        data = request.get_json(force=True)
        model = data.get("model", "qwen2.5vl:72b")
        # model = data.get("model", "gemma3:1b")
        prompt = data.get("prompt", "")
        images = data.get("images", [])

        print(f"💬 Incoming chat:\n - Model: {model}\n - Prompt: {prompt}\n - Images: {images}")
        reply = ollama_vision_generate(model=model, prompt=prompt, images=images)
        return jsonify({"response": reply})
    except Exception as e:
        print(f"❌ Chat API error: {e}")
        return jsonify({"error": str(e)}), 500
    


from flask import send_file
import urllib.parse

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
