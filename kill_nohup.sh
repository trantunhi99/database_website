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
