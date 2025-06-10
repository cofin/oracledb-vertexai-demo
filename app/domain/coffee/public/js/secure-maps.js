/**
 * Secure Google Maps implementation with proper validation and CSP compliance
 */

(function() {
    'use strict';

    // Configuration constants
    const VALID_LAT_RANGE = [-90, 90];
    const VALID_LNG_RANGE = [-180, 180];
    const DEFAULT_ZOOM = 12;
    const MAX_ZOOM = 20;
    const MIN_ZOOM = 1;

    // Validation functions
    function isValidLatitude(lat) {
        const num = parseFloat(lat);
        return !isNaN(num) && num >= VALID_LAT_RANGE[0] && num <= VALID_LAT_RANGE[1];
    }

    function isValidLongitude(lng) {
        const num = parseFloat(lng);
        return !isNaN(num) && num >= VALID_LNG_RANGE[0] && num <= VALID_LNG_RANGE[1];
    }

    function isValidZoom(zoom) {
        const num = parseInt(zoom, 10);
        return !isNaN(num) && num >= MIN_ZOOM && num <= MAX_ZOOM;
    }

    function sanitizeText(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize a single map
    function initializeMap(mapId) {
        const container = document.querySelector(`[data-map-id="${CSS.escape(mapId)}"]`);
        if (!container) {
            console.error(`Map container not found for ID: ${mapId}`);
            return;
        }

        // Get and validate center coordinates
        const centerLat = parseFloat(container.dataset.centerLat);
        const centerLng = parseFloat(container.dataset.centerLng);
        const zoom = parseInt(container.dataset.zoom, 10) || DEFAULT_ZOOM;

        if (!isValidLatitude(centerLat) || !isValidLongitude(centerLng)) {
            console.error('Invalid center coordinates');
            container.innerHTML = '<p style="color: red;">Invalid map coordinates</p>';
            return;
        }

        if (!isValidZoom(zoom)) {
            console.error('Invalid zoom level');
            return;
        }

        // Get location data
        const locationsScript = document.querySelector(`.map-locations-data[data-map-id="${CSS.escape(mapId)}"]`);
        if (!locationsScript) {
            console.error('Location data not found');
            return;
        }

        let locations;
        try {
            locations = JSON.parse(locationsScript.textContent);
        } catch (e) {
            console.error('Invalid location data:', e);
            return;
        }

        // Validate all locations
        const validLocations = locations.filter(loc => {
            return isValidLatitude(loc.latitude) && 
                   isValidLongitude(loc.longitude) &&
                   typeof loc.name === 'string' &&
                   typeof loc.address === 'string';
        });

        if (validLocations.length === 0) {
            console.error('No valid locations found');
            container.innerHTML = '<p style="color: red;">No valid locations to display</p>';
            return;
        }

        // Create map
        const map = new google.maps.Map(container, {
            center: { lat: centerLat, lng: centerLng },
            zoom: zoom,
            mapTypeControl: true,
            streetViewControl: false,
            fullscreenControl: true,
            zoomControl: true,
            // Security: Disable clickable POIs to prevent potential data leakage
            clickableIcons: false,
            // Additional security options
            restriction: {
                latLngBounds: {
                    north: 85,
                    south: -85,
                    east: 180,
                    west: -180
                }
            }
        });

        // Create info window for markers
        const infoWindow = new google.maps.InfoWindow();

        // Add markers for each location
        validLocations.forEach((location, index) => {
            const marker = new google.maps.Marker({
                position: { lat: location.latitude, lng: location.longitude },
                map: map,
                title: sanitizeText(location.name),
                // Use a custom icon or default
                icon: {
                    url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
                    scaledSize: new google.maps.Size(40, 40)
                }
            });

            // Create secure info window content
            const contentDiv = document.createElement('div');
            contentDiv.style.padding = '10px';
            
            const nameElement = document.createElement('h4');
            nameElement.textContent = location.name;
            nameElement.style.margin = '0 0 5px 0';
            
            const addressElement = document.createElement('p');
            addressElement.textContent = location.address;
            addressElement.style.margin = '0';
            addressElement.style.fontSize = '14px';
            
            contentDiv.appendChild(nameElement);
            contentDiv.appendChild(addressElement);

            marker.addListener('click', () => {
                infoWindow.setContent(contentDiv);
                infoWindow.open(map, marker);
            });
        });

        // Adjust bounds to show all markers
        if (validLocations.length > 1) {
            const bounds = new google.maps.LatLngBounds();
            validLocations.forEach(loc => {
                bounds.extend(new google.maps.LatLng(loc.latitude, loc.longitude));
            });
            map.fitBounds(bounds);
        }
    }

    // Global initialization function
    window.initializeSecureMap = function(mapId) {
        if (typeof google === 'undefined' || !google.maps) {
            console.error('Google Maps not loaded');
            return;
        }
        initializeMap(mapId);
    };

    // Process queued maps when Google Maps loads
    window.initializeQueuedMaps = function() {
        if (window.mapInitQueue && Array.isArray(window.mapInitQueue)) {
            window.mapInitQueue.forEach(mapId => {
                initializeMap(mapId);
            });
            window.mapInitQueue = [];
        }
    };

    // Google Maps callback
    window.initGoogleMaps = function() {
        // Initialize any queued maps
        window.initializeQueuedMaps();
        
        // Set up observer for dynamically added maps
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        const mapContainers = node.querySelectorAll('.gmap-container[data-map-id]');
                        mapContainers.forEach(container => {
                            const mapId = container.dataset.mapId;
                            if (mapId) {
                                initializeMap(mapId);
                            }
                        });
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    };

})();