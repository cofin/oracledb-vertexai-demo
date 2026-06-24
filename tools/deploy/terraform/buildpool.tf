# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Establish the servicenetworking peering that the worker pool rides on.
resource "google_service_networking_connection" "coffee_buildpool_peering" {
  network                 = google_compute_network.coffee_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.coffee_buildpool_range.name]
}

# Private Cloud Build worker pool peered to coffee-vpc so the migrate step
# can reach the private Oracle VM at 10.10.0.10:1521.
resource "google_cloudbuild_worker_pool" "coffee_build_pool" {
  name     = "coffee-build-pool"
  location = var.region

  worker_config {
    disk_size_gb   = 100
    machine_type   = "e2-standard-4"
    no_external_ip = false
  }

  network_config {
    peered_network = google_compute_network.coffee_vpc.id
  }

  depends_on = [google_service_networking_connection.coffee_buildpool_peering]
}
