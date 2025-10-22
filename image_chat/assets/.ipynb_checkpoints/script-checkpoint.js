// ========== WANG LAB CHATBOT + ROI MIRROR + REALISTIC EFFECTS ==========
function waitForChatElements() {
  const sendBtn = document.getElementById("sendBtn");
  const chatInput = document.getElementById("chatInput");
  const chatMessages = document.getElementById("chatMessages");

  if (!sendBtn || !chatInput || !chatMessages) {
    return setTimeout(waitForChatElements, 250);
  }

  console.log("✅ Chat elements found, initializing chatbot...");

  // 🧩 Get session ID from mirrored div (NOT dcc.Store)
  function getSessionID() {
    const mirrorEl = document.querySelector('[id="session-id-mirror"]');
    if (mirrorEl && mirrorEl.dataset.dashStore) {
      try {
        const parsed = JSON.parse(mirrorEl.dataset.dashStore);
        if (parsed.session_id) {
          console.log("🧠 Using mirrored session ID:", parsed.session_id);
          return parsed.session_id;
        }
      } catch (err) {
        console.warn("⚠️ Failed to parse session mirror:", err);
      }
    }
    console.warn("⚠️ No mirrored session ID found, defaulting to 'default'");
    return "default";
  }

  // 🗨️ Add message to chat window
  function addMessage(text, sender = "user", imagePaths = []) {
    const msg = document.createElement("div");
    msg.classList.add("chat-message", sender);
    msg.textContent = text;
    msg.style.transition = "opacity 0.3s ease";
    msg.style.opacity = 0;
    chatMessages.appendChild(msg);

    setTimeout(() => {
      msg.style.opacity = 1;
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 50);

    // 🩻 Add thumbnails
    if (imagePaths && imagePaths.length > 0) {
      const thumbContainer = document.createElement("div");
      thumbContainer.classList.add("roi-thumbs");
      thumbContainer.style.marginTop = "8px";
      thumbContainer.style.display = "flex";
      thumbContainer.style.flexWrap = "wrap";
      thumbContainer.style.gap = "6px";

      imagePaths.forEach((path) => {
        const img = document.createElement("img");
        img.src = `/preview?path=${encodeURIComponent(path)}`;
        console.log("🧩 ROI preview URL:", img.src);
        img.alt = "ROI preview";
        img.style.width = "80px";
        img.style.height = "80px";
        img.style.objectFit = "cover";
        img.style.borderRadius = "8px";
        img.style.border = "1px solid #ccc";
        img.style.cursor = "pointer";
        img.title = path;
        img.onclick = () => window.open(img.src, "_blank");
        thumbContainer.appendChild(img);
      });

      msg.appendChild(thumbContainer);
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // 🧠 Get ROI paths
  function getROIPaths() {
    const mirrorEl = document.querySelector('[id="roi-data-mirror"]');
    if (mirrorEl && mirrorEl.dataset.dashStore) {
      try {
        const parsed = JSON.parse(mirrorEl.dataset.dashStore);
        if (parsed.paths?.length) {
          console.log(`🩻 Found ${parsed.paths.length} ROI(s):`, parsed.paths);
          return parsed.paths;
        }
      } catch (err) {
        console.warn("⚠️ Failed to parse ROI mirror:", err);
      }
    }

    console.warn("⚠️ No ROI data found.");
    return [];
  }

  // 🎬 Typing effect
  function typeText(el, text, delay = 25) {
    return new Promise((resolve) => {
      let i = 0;
      const typer = setInterval(() => {
        el.textContent += text.charAt(i);
        i++;
        chatMessages.scrollTop = chatMessages.scrollHeight;
        if (i >= text.length) {
          clearInterval(typer);
          resolve();
        }
      }, delay);
    });
  }

  // ⚙️ AI response handler
  async function aiRespond(userText) {
    let typingAnim;
    const roiPaths = getROIPaths();
    const sessionId = getSessionID();

    // Create thinking bubble
    const thinking = document.createElement("div");
    thinking.classList.add("chat-message", "ai");
    thinking.textContent = "AI: ";
    const dots = document.createElement("span");
    dots.textContent = "…";
    thinking.appendChild(dots);
    chatMessages.appendChild(thinking);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Animate dots (typing)
    let dotCount = 0;
    typingAnim = setInterval(() => {
      dotCount = (dotCount + 1) % 4;
      dots.textContent = ".".repeat(dotCount);
    }, 400);

    try {
      // Build payload with session awareness
      const payload = {
        model: "qwen2.5vl:72b",
        prompt: userText,
        images: roiPaths,
        session_id: sessionId,
      };

      console.log("📡 Sending payload → /api/chat", payload);
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Chat API failed");
      const data = await response.json();

      // Stop typing
      clearInterval(typingAnim);
      dots.remove();

      // Simulate realistic pause
      await new Promise((r) => setTimeout(r, 500 + Math.random() * 800));

      const replyText = data.response || "(no response)";
      thinking.textContent = "AI: ";
      await typeText(thinking, replyText, 20);

      // 🩻 ROI previews
      if (roiPaths.length > 0) {
        const thumbContainer = document.createElement("div");
        thumbContainer.classList.add("roi-thumbs");
        thumbContainer.style.marginTop = "8px";
        thumbContainer.style.display = "flex";
        thumbContainer.style.flexWrap = "wrap";
        thumbContainer.style.gap = "6px";

        roiPaths.forEach((path) => {
          const img = document.createElement("img");
          img.src = `/preview?path=${encodeURIComponent(path)}`;
          img.alt = "ROI preview";
          img.style.width = "80px";
          img.style.height = "80px";
          img.style.objectFit = "cover";
          img.style.borderRadius = "8px";
          img.style.border = "1px solid #ccc";
          img.style.cursor = "pointer";
          img.onclick = () => window.open(img.src, "_blank");
          thumbContainer.appendChild(img);
        });
        thinking.appendChild(thumbContainer);
      }

      chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (err) {
      console.warn("⚠️ AI fetch failed:", err.message);
      clearInterval(typingAnim);
      dots.remove();

      const fallback = document.createElement("div");
      fallback.classList.add("chat-message", "ai");
      fallback.textContent = `AI (Mock): Offline. Echo → "${userText}"`;
      chatMessages.appendChild(fallback);
    }
  }

  // 🚀 Handle user input
  async function handleSend() {
    const text = chatInput.value.trim();
    if (!text) return;
    addMessage(text, "user");
    chatInput.value = "";
    await aiRespond(text);
  }

  // 🎧 Listeners
  sendBtn.addEventListener("click", handleSend);
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  });

  // 👁 Watch ROI mirror updates
  const mirrorEl = document.querySelector('[id="roi-data-mirror"]');
  if (mirrorEl) {
    const observer = new MutationObserver(() => {
      console.log("⚡ ROI mirror updated:", mirrorEl.dataset.dashStore);
    });
    observer.observe(mirrorEl, { attributes: true });
  }
}

// Initialize after Dash mounts
setTimeout(waitForChatElements, 500);
