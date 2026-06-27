// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

const TEAM_WORDS = [
  "SHANE",
  "NASH",
  "MARTIN",
  "ELBOW",
  "KERRY",
  "BOSSMAN",
  "ADRIAN",
  "WARREN",
  "PAYNTER",
  "TIM",
  "NEIL",
  "STEVE",
];

const TECH_WORDS = [
  "BLACK BELT",
  "ORACLE 26AI",
  "VECTOR(3072)",
  "VERTEX AI",
  "GEMINI",
  "☕",
  "🫘",
];

const ALL_WORDS = [...TEAM_WORDS, ...TECH_WORDS];

export function triggerBlackBeltRain() {
  // Prevent duplicate canvas elements
  if (document.getElementById("black-belt-rain-canvas")) {
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.id = "black-belt-rain-canvas";
  canvas.style.position = "fixed";
  canvas.style.top = "0";
  canvas.style.left = "0";
  canvas.style.width = "100vw";
  canvas.style.height = "100vh";
  canvas.style.zIndex = "99999";
  canvas.style.pointerEvents = "none";
  canvas.style.transition = "opacity 2s ease-out";
  document.body.appendChild(canvas);

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Set canvas size to full viewport
  const resizeCanvas = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  };
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  const fontSize = 16;
  const columns = Math.floor(canvas.width / fontSize) + 1;
  const drops = Array(columns).fill(1);
  
  // Track active words falling in columns to draw cohesive vertical names
  const activeColumns = Array(columns).fill(null).map(() => {
    if (Math.random() > 0.85) {
      const word = ALL_WORDS[Math.floor(Math.random() * ALL_WORDS.length)];
      return {
        word,
        index: 0,
      };
    }
    return null;
  });

  const matrixChars = "010101010101ABCDEFHIJKLMNOPQRSTUVWXYZ_@#$%&*+-/=".split("");

  let frameId;
  const start = Date.now();
  const duration = 10000; // 10 seconds

  function draw() {
    // Semi-transparent black background to create trail effect
    ctx.fillStyle = "rgba(10, 10, 10, 0.08)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.font = `${fontSize}px monospace`;

    for (let i = 0; i < drops.length; i++) {
      let char = "";
      let isHighlight = false;

      const columnState = activeColumns[i];
      if (columnState) {
        // Draw the next character of the active word in this stream
        const word = columnState.word;
        char = word[columnState.index];
        columnState.index++;
        isHighlight = true;

        if (columnState.index >= word.length) {
          activeColumns[i] = null; // Word finished
        }
      } else {
        // Standard random matrix char
        char = matrixChars[Math.floor(Math.random() * matrixChars.length)];
        // Chance to spawn a new word in this column
        if (Math.random() > 0.99) {
          activeColumns[i] = {
            word: ALL_WORDS[Math.floor(Math.random() * ALL_WORDS.length)],
            index: 0,
          };
        }
      }

      // Alternate color styling: gold/amber for highlighting team, green for standard matrix rain
      if (isHighlight) {
        ctx.fillStyle = "#fbbf24"; // Tailwind amber-400
        ctx.shadowColor = "#fbbf24";
        ctx.shadowBlur = 10;
      } else {
        ctx.fillStyle = "#10b981"; // Tailwind emerald-500
        ctx.shadowColor = "#10b981";
        ctx.shadowBlur = 4;
      }

      const x = i * fontSize;
      const y = drops[i] * fontSize;

      ctx.fillText(char, x, y);
      ctx.shadowBlur = 0; // Reset shadow

      // Reset drop to top if it reaches bottom, or randomly after a certain point
      if (y > canvas.height && Math.random() > 0.975) {
        drops[i] = 0;
      }

      drops[i]++;
    }

    if (Date.now() - start < duration) {
      frameId = requestAnimationFrame(draw);
    } else {
      // Fade out
      canvas.style.opacity = "0";
      setTimeout(() => {
        window.removeEventListener("resize", resizeCanvas);
        cancelAnimationFrame(frameId);
        canvas.remove();
      }, 2000);
    }
  }

  // Kickoff loop
  draw();
}
