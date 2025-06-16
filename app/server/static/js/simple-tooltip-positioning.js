// Simplified Tooltip Positioning
function positionTooltip(trigger, tooltip) {
  const PADDING = 16;
  const ARROW_SIZE = 10;

  const triggerRect = trigger.getBoundingClientRect();
  const tooltipRect = tooltip.getBoundingClientRect();
  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight,
  };

  // Determine side preference based on trigger position
  const isRightSide = triggerRect.left > viewport.width / 2;

  // Calculate available space
  const space = {
    above: triggerRect.top - PADDING,
    below: viewport.height - triggerRect.bottom - PADDING,
    left: triggerRect.left - PADDING,
    right: viewport.width - triggerRect.right - PADDING,
  };

  let placement, position;

  // For right-side triggers, prefer left placement
  if (isRightSide && space.left >= tooltipRect.width) {
    placement = "left";
    position = {
      left: triggerRect.left - tooltipRect.width - ARROW_SIZE,
      top: triggerRect.top + (triggerRect.height - tooltipRect.height) / 2,
    };
  }
  // For left-side triggers, prefer right placement
  else if (!isRightSide && space.right >= tooltipRect.width) {
    placement = "right";
    position = {
      left: triggerRect.right + ARROW_SIZE,
      top: triggerRect.top + (triggerRect.height - tooltipRect.height) / 2,
    };
  }
  // Fallback to top/bottom
  else if (space.above >= tooltipRect.height) {
    placement = "top";
    position = {
      left: triggerRect.left + (triggerRect.width - tooltipRect.width) / 2,
      top: triggerRect.top - tooltipRect.height - ARROW_SIZE,
    };
  } else {
    placement = "bottom";
    position = {
      left: triggerRect.left + (triggerRect.width - tooltipRect.width) / 2,
      top: triggerRect.bottom + ARROW_SIZE,
    };
  }

  // Constrain to viewport
  position.left = Math.max(
    PADDING,
    Math.min(position.left, viewport.width - tooltipRect.width - PADDING),
  );
  position.top = Math.max(
    PADDING,
    Math.min(position.top, viewport.height - tooltipRect.height - PADDING),
  );

  // Calculate arrow position
  const triggerCenter = {
    x: triggerRect.left + triggerRect.width / 2,
    y: triggerRect.top + triggerRect.height / 2,
  };

  let arrowOffset;
  if (placement === "top" || placement === "bottom") {
    arrowOffset = triggerCenter.x - position.left;
    arrowOffset = Math.max(20, Math.min(arrowOffset, tooltipRect.width - 20));
  } else {
    arrowOffset = triggerCenter.y - position.top;
    arrowOffset = Math.max(20, Math.min(arrowOffset, tooltipRect.height - 20));
  }

  return {
    placement,
    position,
    arrowOffset,
  };
}

// Usage example:
function showSimpleTooltip(trigger, content) {
  const tooltip = document.createElement("div");
  tooltip.className = "help-tooltip";
  tooltip.innerHTML = content;
  tooltip.style.visibility = "hidden";
  document.body.appendChild(tooltip);

  const result = positionTooltip(trigger, tooltip);

  tooltip.style.left = result.position.left + "px";
  tooltip.style.top = result.position.top + "px";
  tooltip.setAttribute("data-placement", result.placement);

  if (result.placement === "top" || result.placement === "bottom") {
    tooltip.style.setProperty("--arrow-offset", result.arrowOffset + "px");
  } else {
    tooltip.style.setProperty("--arrow-offset-y", result.arrowOffset + "px");
  }

  tooltip.style.visibility = "visible";
  tooltip.classList.add("show");

  return tooltip;
}
