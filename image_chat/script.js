console.log("✅ script.js loaded");

const map = L.map("map", {
  crs: L.CRS.Simple,
  minZoom: -4
});

const bounds = [[0,0], [2000,2000]]; // change to match your image pixel size
L.imageOverlay("https://upload.wikimedia.org/wikipedia/commons/3/3c/Shaki_waterfall.jpg", bounds).addTo(map);

map.fitBounds(bounds);


// Feature group for drawn shapes
const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

// Drawing controls
const drawControl = new L.Control.Draw({
  edit: { featureGroup: drawnItems },
  draw: {
    rectangle: true,
    polygon: true,
    circle: true,
    polyline: false,
    marker: true
  }
});
map.addControl(drawControl);

// Handle shape creation
map.on(L.Draw.Event.CREATED, function (e) {
  const layer = e.layer;
  drawnItems.addLayer(layer);

  const type = e.layerType;
  let regionInfo = "";

  if (type === "rectangle" || type === "polygon") {
  const coords = layer.getLatLngs()[0]; // first ring
  regionInfo = `${type} with coords: ` + coords.map(c => `(${c.lng.toFixed(2)}, ${c.lat.toFixed(2)})`).join(", ");
} 
else if (type === "circle") {
  const center = layer.getLatLng();
  const radius = layer.getRadius();
  regionInfo = `circle center=(${center.lng.toFixed(2)}, ${center.lat.toFixed(2)}), radius=${radius.toFixed(2)}px`;
} 
else if (type === "marker") {
  const pos = layer.getLatLng();
  regionInfo = `marker at (${pos.lng.toFixed(2)}, ${pos.lat.toFixed(2)})`;
}


  addMessage(`Selected ${regionInfo}`, "user");
  aiRespond(`I see you drew a ${regionInfo}. This might highlight important tissue features.`);
});

// ---- CHATBOT ---- //
const sendBtn = document.getElementById("sendBtn");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");

function addMessage(text, sender = "user") {
  const msg = document.createElement("div");
  msg.classList.add("chat-message", sender);
  msg.textContent = text;
  chatMessages.appendChild(msg);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Try API first, fallback to mock if it fails
async function aiRespond(userText) {
  try {
    // Temporary "thinking..." placeholder
    const thinking = document.createElement("div");
    thinking.classList.add("chat-message", "ai");
    thinking.textContent = "AI is typing...";
    chatMessages.appendChild(thinking);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_API_KEY" // replace or proxy through backend
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [
          { role: "system", content: "You are a biology assistant analyzing tissue images." },
          { role: "user", content: userText }
        ]
      })
    });

    if (!response.ok) throw new Error("API request failed");

    const data = await response.json();
    const aiText = data.choices?.[0]?.message?.content?.trim();

    // Replace placeholder
    thinking.remove();
    if (aiText) {
      addMessage(aiText, "ai");
    } else {
      addMessage("⚠️ API gave empty response.", "ai");
    }

  } catch (err) {
    console.warn("API failed, fallback to mock →", err.message);

    // Remove placeholder if still there
    const last = chatMessages.lastChild;
    if (last && last.textContent === "AI is typing...") last.remove();

    // Mock fallback
    setTimeout(() => {
      addMessage("AI: Analyzing → " + userText, "ai");
    }, 600);
  }
}

sendBtn.addEventListener("click", () => {
  const text = chatInput.value.trim();
  if (text) {
    addMessage(text, "user");
    chatInput.value = "";
    aiRespond(text);
  }
});

chatInput.addEventListener("keypress", e => {
  if (e.key === "Enter") sendBtn.click();
});

