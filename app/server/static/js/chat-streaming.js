/**
 * chat-streaming.js - SSE (Server-Sent Events) handler for real-time AI responses
 *
 * Handles progressive streaming of AI responses via HTMX SSE extension.
 * Listens for chunk, metadata, complete, and error events.
 */

// Handle SSE message events
document.body.addEventListener("htmx:sseMessage", function (evt) {
  const msgType = evt.detail.type;

  if (msgType === "chunk") {
    // Progressive text rendering
    const data = JSON.parse(evt.detail.data);
    const responseEl = evt.target.querySelector(".ai-response-content");
    if (responseEl) {
      // Remove typing indicator on first chunk
      const typingIndicator = responseEl.querySelector(".typing-indicator");
      if (typingIndicator) {
        typingIndicator.remove();
      }
      // Append text progressively
      responseEl.textContent += data.text;

      // Auto-scroll to bottom
      const container = document.getElementById("chat-container");
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  } else if (msgType === "metadata") {
    // Store metadata for tooltips (intent, products)
    const data = JSON.parse(evt.detail.data);
    // Can be used to populate help tooltips with query details
    console.log("Metadata received:", data.type, data.data);
  } else if (msgType === "complete") {
    // Streaming complete - show help buttons with smooth transition
    const data = JSON.parse(evt.detail.data);
    console.log("Stream complete:", data);

    // Show help buttons with a slight delay for smooth appearance
    setTimeout(() => {
      const helpTriggers = evt.target.querySelector(".help-triggers");
      if (helpTriggers) {
        helpTriggers.style.display = "inline-flex";
        // Force reflow for animation
        helpTriggers.offsetHeight;
      }
    }, 200);

    // Smooth scroll to bottom
    const container = document.getElementById("chat-container");
    if (container) {
      // Use smooth scroll behavior
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    }

    // Reload metrics after completion
    setTimeout(() => {
      if (typeof loadMetrics === "function") {
        loadMetrics();
      }
    }, 500);
  } else if (msgType === "error") {
    // Error handling
    const data = JSON.parse(evt.detail.data);
    console.error("SSE error:", data.error);

    const responseEl = evt.target.querySelector(".ai-response-content");
    if (responseEl) {
      responseEl.innerHTML =
        '<span style="color: #d32f2f;">Error: ' + data.error + "</span>";
    }

    // Remove loading class
    evt.target.classList.remove("loading");
  }
});

// Handle SSE errors (connection issues)
document.body.addEventListener("htmx:sseError", function (evt) {
  console.error("SSE connection error:", evt.detail);

  const responseEl = evt.target.querySelector(".ai-response-content");
  if (responseEl) {
    // Remove typing indicator
    const typingIndicator = responseEl.querySelector(".typing-indicator");
    if (typingIndicator) {
      typingIndicator.remove();
    }
    responseEl.innerHTML =
      '<span style="color: #d32f2f;">Connection error. Please try again.</span>';
  }

  evt.target.classList.remove("loading");
});

// Handle SSE open (connection established)
document.body.addEventListener("htmx:sseOpen", function (evt) {
  console.log("SSE connection opened");
});
