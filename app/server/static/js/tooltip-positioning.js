// Enhanced Tooltip Positioning System
class TooltipPositioner {
  constructor(options = {}) {
    this.padding = options.padding || 16;
    this.arrowSize = options.arrowSize || 10;
    this.preferredPlacements = options.preferredPlacements || {
      left: ["right", "left", "top", "bottom"],
      right: ["left", "right", "top", "bottom"],
    };
  }

  /**
   * Calculate optimal tooltip position with viewport awareness
   * @param {HTMLElement} trigger - The trigger element (help button)
   * @param {HTMLElement} tooltip - The tooltip element
   * @param {Object} options - Additional options
   * @returns {Object} Position and placement data
   */
  calculatePosition(trigger, tooltip, options = {}) {
    const triggerRect = trigger.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollX: window.pageXOffset,
      scrollY: window.pageYOffset,
    };

    // Determine if trigger is on left or right side of viewport
    const isRightSide = triggerRect.left > viewport.width / 2;
    const preferredPlacements = isRightSide
      ? this.preferredPlacements.right
      : this.preferredPlacements.left;

    // Try each placement in order of preference
    for (const placement of preferredPlacements) {
      const position = this.getPositionForPlacement(
        placement,
        triggerRect,
        tooltipRect,
        viewport,
      );

      if (this.isPositionValid(position, tooltipRect, viewport)) {
        return {
          ...position,
          placement,
          arrow: this.calculateArrowPosition(
            placement,
            triggerRect,
            position,
            tooltipRect,
          ),
        };
      }
    }

    // Fallback: find the best fit even if partially out of viewport
    return this.getBestFitPosition(triggerRect, tooltipRect, viewport);
  }

  getPositionForPlacement(placement, triggerRect, tooltipRect, viewport) {
    const positions = {
      top: {
        left: triggerRect.left + (triggerRect.width - tooltipRect.width) / 2,
        top:
          triggerRect.top - tooltipRect.height - this.arrowSize - this.padding,
      },
      bottom: {
        left: triggerRect.left + (triggerRect.width - tooltipRect.width) / 2,
        top: triggerRect.bottom + this.arrowSize + this.padding,
      },
      left: {
        left:
          triggerRect.left - tooltipRect.width - this.arrowSize - this.padding,
        top: triggerRect.top + (triggerRect.height - tooltipRect.height) / 2,
      },
      right: {
        left: triggerRect.right + this.arrowSize + this.padding,
        top: triggerRect.top + (triggerRect.height - tooltipRect.height) / 2,
      },
    };

    // Add scroll offset
    const position = positions[placement];
    return {
      left: position.left + viewport.scrollX,
      top: position.top + viewport.scrollY,
    };
  }

  isPositionValid(position, tooltipRect, viewport) {
    const bounds = {
      left: position.left - viewport.scrollX,
      top: position.top - viewport.scrollY,
      right: position.left - viewport.scrollX + tooltipRect.width,
      bottom: position.top - viewport.scrollY + tooltipRect.height,
    };

    return (
      bounds.left >= this.padding &&
      bounds.top >= this.padding &&
      bounds.right <= viewport.width - this.padding &&
      bounds.bottom <= viewport.height - this.padding
    );
  }

  getBestFitPosition(triggerRect, tooltipRect, viewport) {
    // Calculate how much space is available in each direction
    const space = {
      top: triggerRect.top,
      bottom: viewport.height - triggerRect.bottom,
      left: triggerRect.left,
      right: viewport.width - triggerRect.right,
    };

    // For right-side elements, prefer left placement
    if (triggerRect.left > viewport.width / 2) {
      if (space.left >= tooltipRect.width + this.padding) {
        return this.getPositionForPlacement(
          "left",
          triggerRect,
          tooltipRect,
          viewport,
        );
      }
    }

    // Find the direction with most space
    const bestDirection = Object.keys(space).reduce((a, b) =>
      space[a] > space[b] ? a : b,
    );

    let position = this.getPositionForPlacement(
      bestDirection,
      triggerRect,
      tooltipRect,
      viewport,
    );

    // Constrain to viewport
    position = this.constrainToViewport(position, tooltipRect, viewport);

    return {
      ...position,
      placement: bestDirection,
      arrow: this.calculateArrowPosition(
        bestDirection,
        triggerRect,
        position,
        tooltipRect,
      ),
    };
  }

  constrainToViewport(position, tooltipRect, viewport) {
    return {
      left: Math.max(
        this.padding + viewport.scrollX,
        Math.min(
          position.left,
          viewport.width - tooltipRect.width - this.padding + viewport.scrollX,
        ),
      ),
      top: Math.max(
        this.padding + viewport.scrollY,
        Math.min(
          position.top,
          viewport.height -
            tooltipRect.height -
            this.padding +
            viewport.scrollY,
        ),
      ),
    };
  }

  calculateArrowPosition(placement, triggerRect, tooltipPosition, tooltipRect) {
    const triggerCenter = {
      x: triggerRect.left + triggerRect.width / 2,
      y: triggerRect.top + triggerRect.height / 2,
    };

    const arrow = {
      placement,
      offset: null,
      rotation: 0,
    };

    switch (placement) {
      case "top":
      case "bottom":
        // Calculate horizontal offset for arrow to point at trigger center
        const tooltipLeft = tooltipPosition.left - window.pageXOffset;
        arrow.offset = Math.max(
          this.arrowSize,
          Math.min(
            triggerCenter.x - tooltipLeft,
            tooltipRect.width - this.arrowSize,
          ),
        );
        arrow.rotation = placement === "top" ? 180 : 0;
        break;

      case "left":
      case "right":
        // Calculate vertical offset for arrow to point at trigger center
        const tooltipTop = tooltipPosition.top - window.pageYOffset;
        arrow.offset = Math.max(
          this.arrowSize,
          Math.min(
            triggerCenter.y - tooltipTop,
            tooltipRect.height - this.arrowSize,
          ),
        );
        arrow.rotation = placement === "left" ? 90 : -90;
        break;
    }

    return arrow;
  }
}

// Export for use in help-tooltips-htmx.js
window.TooltipPositioner = TooltipPositioner;
