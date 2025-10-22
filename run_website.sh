#!/bin/bash
# 🚀 Wang Lab Dash App + HTTP Server Launcher
# ===============================================

source ~/.bashrc
conda activate /condo/wanglab/tmhtxt85/conda_envs/mjolnir

# --- Configurable Ports ---
DASH_PORT=8050
HTTP_PORT=8083
MODEL_PORT=11434
TILE_PORT=9015

# --- Detect environment ---
USER_NAME=$(whoami)
NODE_NAME=$(hostname)

# --- Kill existing nohup jobs (user-owned only) ---
echo "🧹 Checking for existing Dash or HTTP servers..."
PIDS=$(ps aux | grep "$USER" | grep -E "image_chat_app.py|http.server" | grep -v "grep" | awk '{print $2}')

if [ -n "$PIDS" ]; then
  echo "⚠️  Found running processes: $PIDS"
  echo "🔪 Killing them..."
  kill -9 $PIDS 2>/dev/null
  echo "✅ Previous Dash/HTTP servers terminated."
else
  echo "✨ No existing Dash or HTTP processes found."
fi


# --- Run Dash app ---
echo "🧠 Starting Dash app on port $DASH_PORT..."
nohup python ./image_chat/image_chat_app.py > ./dash_$DASH_PORT.log 2>&1 &
DASH_PID=$!

# --- Run HTTP file server ---
echo "🖼️ Starting Python HTTP server on port $HTTP_PORT..."
nohup python3 -m http.server $HTTP_PORT > ./http_$HTTP_PORT.log 2>&1 &
HTTP_PID=$!

# --- Summary Output ---
echo ""
echo "✅ Dash app running on: http://$NODE_NAME:$DASH_PORT"
echo "✅ HTTP preview server: http://$NODE_NAME:$HTTP_PORT"
echo "✅ TileClient server:   http://$NODE_NAME:$TILE_PORT"
echo "✅ Model expected on:   $MODEL_PORT"
echo ""
echo "📄 Logs:"
echo "   - Dash:  ./dash_$DASH_PORT.log"
echo "   - HTTP:  ./http_$HTTP_PORT.log"
echo ""
echo "🧩 Running PIDs:"
echo "   - Dash PID:  $DASH_PID"
echo "   - HTTP PID:  $HTTP_PID"
echo ""
echo "🔗 Run this on your laptop to start port forwarding:"
echo ""
echo "ssh -L $HTTP_PORT:$NODE_NAME:$HTTP_PORT \\"
echo "    -L $DASH_PORT:$NODE_NAME:$DASH_PORT \\"
echo "    -L $TILE_PORT:$NODE_NAME:$TILE_PORT \\"
echo "    -L $((TILE_PORT-1)):$NODE_NAME:$((TILE_PORT-1)) \\"
echo "    $USER_NAME@hpc.tmh.tmhs"
echo ""
echo "💡 Once tunneled, open in your browser:"
echo "   👉 http://localhost:$HTTP_PORT/landing.html"
echo ""

# --- SSH port model to website ---
echo "Porting model...."
ssh -t $USER_NAME@hpcdev.tmh.tmhs -L 11434:localhost:11435 ssh cn058 -L 11435:localhost:11434
