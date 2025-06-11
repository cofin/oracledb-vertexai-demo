// Secure Google Maps implementation
class SecureMaps {
  constructor() {
    this.mapInstances = new Map();
  }

  // Validate coordinates
  validateCoordinate(lat, lng) {
    const latitude = parseFloat(lat);
    const longitude = parseFloat(lng);

    if (isNaN(latitude) || isNaN(longitude)) {
      return null;
    }

    if (
      latitude < -90 ||
      latitude > 90 ||
      longitude < -180 ||
      longitude > 180
    ) {
      return null;
    }

    return { lat: latitude, lng: longitude };
  }

  // Sanitize text content
  sanitizeText(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Initialize map from data attributes
  initializeMap(mapElement) {
    if (!mapElement || this.mapInstances.has(mapElement)) {
      return;
    }

    try {
      const mapData = mapElement.dataset.mapData;
      if (!mapData) return;

      const data = JSON.parse(mapData);
      const center = this.validateCoordinate(data.center.lat, data.center.lng);

      if (!center) {
        console.error("Invalid center coordinates");
        return;
      }

      // Create map with restrictions
      const map = new google.maps.Map(mapElement, {
        center: center,
        zoom: parseInt(data.zoom) || 12,
        mapId: "COFFEE_MAPS",
        // Restrict map interaction to prevent abuse
        restriction: {
          latLngBounds: {
            north: 85,
            south: -85,
            east: 180,
            west: -180,
          },
        },
        // Disable some controls for cleaner UI
        mapTypeControl: false,
        streetViewControl: false,
      });

      this.mapInstances.set(mapElement, map);

      // Add markers for locations
      if (data.locations && Array.isArray(data.locations)) {
        data.locations.forEach((location) => {
          const position = this.validateCoordinate(location.lat, location.lng);
          if (!position) return;

          const marker = new google.maps.marker.AdvancedMarkerElement({
            map: map,
            position: position,
            title: this.sanitizeText(location.name),
            content: this.createMarkerContent(location.name),
          });
        });
      }
    } catch (error) {
      console.error("Error initializing map:", error);
    }
  }

  // Create secure marker content
  createMarkerContent(name) {
    const content = document.createElement("div");
    content.style.cssText =
      "background: #967259; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;";
    content.textContent = name; // Safe text content
    return content;
  }

  // Initialize all maps on page
  initializeAllMaps() {
    const mapElements = document.querySelectorAll("[data-map-data]");
    mapElements.forEach((element) => this.initializeMap(element));
  }
}

// Export for use
window.SecureMaps = SecureMaps;
