// Simple Help Tooltips with HTMX

// Default to enabled for tech demo
let helpEnabled = localStorage.getItem("helpTooltipsEnabled") !== "false";
let activeTooltip = null;

// Toggle help mode
function toggleHelp() {
  helpEnabled = !helpEnabled;
  localStorage.setItem("helpTooltipsEnabled", helpEnabled.toString());

  // Update button text
  const button = document.querySelector(".help-toggle");
  if (button) {
    button.textContent = helpEnabled ? "✓" : "💡";
    button.classList.toggle("active", helpEnabled);
  }

  // Show/hide help elements
  document.querySelectorAll(".help-trigger").forEach((el) => {
    // Always use inline-flex for proper alignment
    el.style.display = helpEnabled ? "inline-flex" : "none";
  });

  // Close any open tooltip
  hideTooltip();
}

// Initialize tooltip positioner
const tooltipPositioner = new TooltipPositioner({
  padding: 16,
  arrowSize: 10,
  preferredPlacements: {
    left: ["right", "left", "top", "bottom"],
    right: ["left", "right", "top", "bottom"],
  },
});

// Show tooltip
function showTooltip(triggerId, triggerElement) {
  // Hide existing tooltip
  hideTooltip();

  // Create tooltip
  const tooltip = document.createElement("div");
  tooltip.className = "help-tooltip";
  tooltip.innerHTML = getTooltipHTML(triggerId);

  // Update dynamic content for intent detection
  if (triggerId === "intent-detection") {
    updateIntentTooltipContent(tooltip, triggerElement);
  }

  // Update dynamic content for performance summary
  if (triggerId === "performance-summary") {
    updatePerformanceTooltipContent(tooltip, triggerElement);
  }

  // Add to body but keep it invisible for measurement
  tooltip.style.visibility = "hidden";
  tooltip.style.display = "block";
  document.body.appendChild(tooltip);

  // Use wider width for cache-related tooltips
  const isCacheTooltip = triggerId.includes("cache");
  if (isCacheTooltip) {
    tooltip.style.maxWidth = "var(--tooltip-cache-width)";
  }

  // Calculate optimal position using the enhanced positioner
  const position = tooltipPositioner.calculatePosition(triggerElement, tooltip);

  // Apply position
  tooltip.style.left = position.left + "px";
  tooltip.style.top = position.top + "px";
  tooltip.setAttribute("data-placement", position.placement);

  // Apply arrow position
  if (position.arrow) {
    if (position.placement === "top" || position.placement === "bottom") {
      tooltip.style.setProperty("--arrow-offset", position.arrow.offset + "px");
    } else {
      tooltip.style.setProperty(
        "--arrow-offset-y",
        position.arrow.offset + "px",
      );
    }
  }

  // Make visible and animate in
  tooltip.style.visibility = "visible";
  requestAnimationFrame(() => {
    tooltip.classList.add("show");
  });

  activeTooltip = tooltip;

  // Add close handler
  const closeBtn = tooltip.querySelector(".help-tooltip-close");
  if (closeBtn) {
    closeBtn.onclick = hideTooltip;
  }

  // Handle window resize
  const resizeHandler = () => {
    if (activeTooltip) {
      const newPosition = tooltipPositioner.calculatePosition(
        triggerElement,
        tooltip,
      );
      tooltip.style.left = newPosition.left + "px";
      tooltip.style.top = newPosition.top + "px";
      tooltip.setAttribute("data-placement", newPosition.placement);

      if (newPosition.arrow) {
        if (
          newPosition.placement === "top" ||
          newPosition.placement === "bottom"
        ) {
          tooltip.style.setProperty(
            "--arrow-offset",
            newPosition.arrow.offset + "px",
          );
        } else {
          tooltip.style.setProperty(
            "--arrow-offset-y",
            newPosition.arrow.offset + "px",
          );
        }
      }
    }
  };

  window.addEventListener("resize", resizeHandler);
  tooltip._resizeHandler = resizeHandler;
}

// Hide tooltip
function hideTooltip() {
  if (activeTooltip) {
    // Remove resize handler
    if (activeTooltip._resizeHandler) {
      window.removeEventListener("resize", activeTooltip._resizeHandler);
    }

    activeTooltip.classList.remove("show");
    setTimeout(() => {
      activeTooltip?.remove();
      activeTooltip = null;
    }, 200);
  }
}

// Get tooltip HTML content
function getTooltipHTML(triggerId) {
  const contents = {
    "input-processing": {
      title: "1️⃣ User Input Processing",
      body: `
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">What Happens</div>
                    <ul style="margin: 8px 0; padding-left: 20px;">
                        <li>HTML tags are stripped for security</li>
                        <li>Input limited to 500 characters</li>
                        <li>Persona context is added to the query</li>
                    </ul>
                </div>
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">Security Code</div>
                    <pre><code>message = re.sub(r'&lt;[^&gt;]+&gt;', '', message)
message = message[:500].strip()</code></pre>
                </div>
            `,
    },
    "intent-detection": {
      title: "🎯 Intent Detection",
      body: `
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">Oracle Vector Search Query</div>
                    <pre><code>SELECT intent_type,
       VECTOR_DISTANCE(embedding,
         :query_embedding, COSINE) AS similarity
FROM intent_exemplars
WHERE VECTOR_DISTANCE(embedding,
        :query_embedding, COSINE) < 0.3
ORDER BY similarity
FETCH FIRST 1 ROW ONLY</code></pre>
                </div>
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">Detection Results</div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Intent</span>
                        <span class="help-tooltip-metric-value" id="detected-intent-value">PRODUCT_RAG</span>
                    </div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Type</span>
                        <span class="help-tooltip-metric-value" id="intent-type-desc">Product Search</span>
                    </div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Processing Time</span>
                        <span class="help-tooltip-metric-value">2.3ms</span>
                    </div>
                </div>
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">What This Means</div>
                    <p id="intent-explanation" style="margin: 8px 0; color: rgba(255,255,255,0.8); font-size: 13px;">
                        Your query was classified as a product search, which triggers vector similarity
                        search against our coffee product database using Oracle 23AI.
                    </p>
                </div>
            `,
    },
    "vector-search": {
      title: "🔍 Product Vector Search",
      body: `
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">Oracle SQL Query</div>
                    <pre><code>SELECT p.product_name,
       p.product_description,
       VECTOR_DISTANCE(p.product_embedding,
         :query_embedding, COSINE) AS similarity
FROM products p
JOIN inventory i ON p.product_id = i.product_id
WHERE VECTOR_DISTANCE(p.product_embedding,
        :query_embedding, COSINE) < 0.5
ORDER BY similarity
FETCH FIRST 4 ROWS ONLY</code></pre>
                </div>
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">Results</div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Oracle Time</span>
                        <span class="help-tooltip-metric-value">8.7ms</span>
                    </div>
                </div>
            `,
    },
    "cache-status": {
      title: "💾 Cache Status",
      body: `
                <div class="help-tooltip-section">
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Cache Type</span>
                        <span class="help-tooltip-metric-value">RESPONSE_CACHE</span>
                    </div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Status</span>
                        <span class="help-tooltip-badge info">🔄 MISS</span>
                    </div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">TTL</span>
                        <span class="help-tooltip-metric-value">300 seconds</span>
                    </div>
                </div>
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">Cache Stats</div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Hit Rate</span>
                        <span class="help-tooltip-metric-value">78%</span>
                    </div>
                </div>
            `,
    },
    "response-cache-hit": {
      title: "⚡ Response Cache Hit",
      body: `
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">Cache Performance</div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Status</span>
                        <span class="help-tooltip-badge success">⚡ HIT</span>
                    </div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Source</span>
                        <span class="help-tooltip-metric-value">Response Cache</span>
                    </div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Time Saved</span>
                        <span class="help-tooltip-metric-value">~1500ms</span>
                    </div>
                </div>
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">What This Means</div>
                    <p style="margin: 8px 0; color: rgba(255,255,255,0.8); font-size: 13px;">
                        This response was retrieved from Oracle's response cache, avoiding the need to
                        generate a new response from Vertex AI. This saves time and reduces costs.
                    </p>
                </div>
            `,
    },
    "embedding-cache-hit": {
      title: "🧠 Embedding Cache Hit",
      body: `
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">Cache Performance</div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Status</span>
                        <span class="help-tooltip-badge success">🧠 HIT</span>
                    </div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Source</span>
                        <span class="help-tooltip-metric-value">Embedding Cache</span>
                    </div>
                    <div class="help-tooltip-metric">
                        <span class="help-tooltip-metric-label">Vector Dimensions</span>
                        <span class="help-tooltip-metric-value">768</span>
                    </div>
                </div>
                <div class="help-tooltip-section">
                    <div class="help-tooltip-section-title">What This Means</div>
                    <p style="margin: 8px 0; color: rgba(255,255,255,0.8); font-size: 13px;">
                        The vector embedding for this query was found in Oracle's native VECTOR cache,
                        avoiding the need to generate new embeddings via Vertex AI.
                    </p>
                </div>
            `,
    },
    "performance-summary": {
      title: "📊 Performance Breakdown",
      body: `
                <div class="help-tooltip-section">
                    <div id="perf-loading" style="text-align: center; padding: 20px; color: rgba(255,255,255,0.7);">
                        Loading performance data...
                    </div>
                    <div id="perf-content" style="display: none;">
                        <!-- Dynamic content will be inserted here -->
                    </div>
                </div>
            `,
    },
  };

  const content = contents[triggerId] || {
    title: "Unknown",
    body: "No content available",
  };

  return `
        <div class="help-tooltip-content">
            <div class="help-tooltip-header">
                <h3 class="help-tooltip-title">${content.title}</h3>
                <button class="help-tooltip-close" type="button">×</button>
            </div>
            <div class="help-tooltip-body">
                ${content.body}
            </div>
        </div>
    `;
}

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
  // Set initial state
  const button = document.querySelector(".help-toggle");
  if (button) {
    button.textContent = helpEnabled ? "✓" : "💡";
    button.classList.toggle("active", helpEnabled);
  }

  // Show/hide help elements based on initial state
  document.querySelectorAll(".help-trigger").forEach((el) => {
    el.style.display = helpEnabled ? "inline-flex" : "none";
  });
});

// Handle clicks outside tooltips
document.addEventListener("click", (e) => {
  if (
    activeTooltip &&
    !activeTooltip.contains(e.target) &&
    !e.target.closest(".help-trigger")
  ) {
    hideTooltip();
  }
});

// Handle HTMX events to show help triggers in newly loaded content
document.body.addEventListener("htmx:afterRequest", () => {
  // Always check current state and show/hide accordingly
  setTimeout(() => {
    document.querySelectorAll(".help-trigger").forEach((el) => {
      el.style.display = helpEnabled ? "inline-flex" : "none";
    });
  }, 100);
});

// Update performance tooltip content
async function updatePerformanceTooltipContent(tooltip, triggerElement) {
  const loadingEl = tooltip.querySelector("#perf-loading");
  const contentEl = tooltip.querySelector("#perf-content");

  // Get message ID from parent message element
  const messageEl = triggerElement.closest(".message");
  const messageId = messageEl ? messageEl.dataset.messageId : null;

  if (!messageId) {
    if (loadingEl) loadingEl.textContent = "Performance data not available";
    return;
  }

  try {
    // Check if this was a response cache hit using the data attribute
    const isCacheHit = messageEl.dataset.fromCache === "true";

    if (isCacheHit) {
      // For cache hits, show simplified performance data
      if (loadingEl) loadingEl.style.display = "none";
      if (contentEl) {
        contentEl.style.display = "block";
        contentEl.innerHTML = `
                    <div class="help-tooltip-metric" style="margin-bottom: 16px;">
                        <span class="help-tooltip-metric-label">Response Type</span>
                        <span class="help-tooltip-metric-value" style="color: #10b981;">⚡ Cached Response</span>
                    </div>
                    <div class="perf-chart">
                        <div class="perf-bar">
                            <div class="perf-bar-label">Cache Lookup</div>
                            <div class="perf-bar-track">
                                <div class="perf-bar-fill" style="width: 100%; background: #10b981"></div>
                            </div>
                            <div class="perf-bar-value">&lt;10ms</div>
                        </div>
                    </div>
                    <div class="help-tooltip-metric" style="margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 16px;">
                        <span class="help-tooltip-metric-label">Total Time</span>
                        <span class="help-tooltip-metric-value" style="color: #10b981;">&lt;50ms</span>
                    </div>
                    <div style="margin-top: 16px; padding: 12px; background: rgba(16, 185, 129, 0.1); border-radius: 8px;">
                        <p style="margin: 0; color: rgba(255,255,255,0.8); font-size: 13px;">
                            This response was served from cache, bypassing embedding generation and LLM processing.
                        </p>
                    </div>
                `;
      }
    } else {
      // For non-cached responses, fetch actual performance data
      const response = await fetch(`/api/help/query-log/${messageId}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json();

      if (loadingEl) loadingEl.style.display = "none";
      if (contentEl) {
        contentEl.style.display = "block";

        const times = data.execution_times || {};
        const total = times.total;

        // Only show bars for metrics that have real data
        const realMetrics = [];
        if (
          times.embedding_generation != null &&
          times.embedding_generation > 0
        ) {
          realMetrics.push({
            label: "Embedding Generation",
            value: times.embedding_generation,
            color: "#8b5cf6",
          });
        }
        if (times.vector_search != null && times.vector_search > 0) {
          realMetrics.push({
            label: "Oracle Vector Search",
            value: times.vector_search,
            color: "#10b981",
          });
        }

        // If we have a total time but no component times, estimate the breakdown
        if (
          realMetrics.length === 0 &&
          times.total != null &&
          times.total > 0
        ) {
          // This likely means we're looking at a general conversation without vector search
          realMetrics.push({
            label: "AI Response Generation",
            value: times.total * 0.95, // Estimate 95% is AI generation
            color: "#f59e0b",
          });
          realMetrics.push({
            label: "Processing Overhead",
            value: times.total * 0.05, // Estimate 5% is overhead
            color: "#6366f1",
          });
        }

        if (realMetrics.length === 0) {
          contentEl.innerHTML = `
            <div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.7);">
              Performance metrics not available for this query
            </div>
          `;
          return;
        }

        // Calculate percentages for bar widths
        const maxTime = Math.max(...realMetrics.map((m) => m.value));

        const barsHtml = realMetrics
          .map(
            (metric) => `
          <div class="perf-bar">
            <div class="perf-bar-label">${metric.label}</div>
            <div class="perf-bar-track">
              <div class="perf-bar-fill" style="width: ${(metric.value / maxTime) * 100}%; background: ${metric.color}"></div>
            </div>
            <div class="perf-bar-value">${metric.value.toFixed(1)}ms</div>
          </div>
        `,
          )
          .join("");

        contentEl.innerHTML = `
          <div class="perf-chart">
            ${barsHtml}
          </div>
          ${
            total != null
              ? `
          <div class="help-tooltip-metric" style="margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 16px;">
            <span class="help-tooltip-metric-label">Total Time</span>
            <span class="help-tooltip-metric-value">${total.toFixed(0)}ms</span>
          </div>
          `
              : ""
          }
        `;
      }
    }
  } catch (error) {
    console.error("Error loading performance data:", error);
    if (loadingEl) loadingEl.textContent = "Error loading performance data";
  }
}

// Update intent tooltip content based on detected intent
function updateIntentTooltipContent(tooltip, triggerElement) {
  // Get the intent from the trigger element's title
  const titleText = triggerElement.getAttribute("title");
  const intent = titleText
    ? titleText.replace("Intent: ", "")
    : "GENERAL_CONVERSATION";

  // Update the intent value
  const intentValueEl = tooltip.querySelector("#detected-intent-value");
  if (intentValueEl) {
    intentValueEl.textContent = intent;
  }

  // Update type description and explanation based on intent
  const typeDescEl = tooltip.querySelector("#intent-type-desc");
  const explanationEl = tooltip.querySelector("#intent-explanation");

  if (typeDescEl && explanationEl) {
    if (intent === "PRODUCT_RAG") {
      typeDescEl.textContent = "Product Search";
      explanationEl.textContent =
        "Your query was classified as a product search, which triggers vector similarity search against our coffee product database using Oracle 23AI.";
    } else {
      typeDescEl.textContent = "General Conversation";
      explanationEl.textContent =
        "Your query was classified as general conversation, which uses a conversational AI approach without product database search.";
    }
  }
}
