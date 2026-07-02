resource "google_compute_network" "coffee_vpc" {
  name                    = "coffee-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "coffee_subnet" {
  name          = "coffee-subnet"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.coffee_vpc.id
}

resource "google_compute_subnetwork" "coffee_run_subnet" {
  name          = "coffee-run-subnet"
  ip_cidr_range = "10.10.1.0/24"
  region        = var.region
  network       = google_compute_network.coffee_vpc.id
}

resource "google_compute_address" "coffee_db_ip" {
  name         = "coffee-db-ip"
  address_type = "INTERNAL"
  address      = "10.10.0.10"
  subnetwork   = google_compute_subnetwork.coffee_subnet.id
  region       = var.region
}

# Reserved range for the Ch3 Cloud Build private pool VPC peering.
resource "google_compute_global_address" "coffee_buildpool_range" {
  name          = "coffee-buildpool-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  address       = "10.30.0.0"
  prefix_length = 24
  network       = google_compute_network.coffee_vpc.id
}

resource "google_compute_router" "coffee_router" {
  name    = "coffee-router"
  region  = var.region
  network = google_compute_network.coffee_vpc.id
}

resource "google_compute_router_nat" "coffee_nat" {
  name                               = "coffee-nat"
  router                             = google_compute_router.coffee_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

resource "google_compute_firewall" "coffee_allow_iap_ssh" {
  name      = "coffee-allow-iap-ssh"
  network   = google_compute_network.coffee_vpc.id
  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"] # Google IAP TCP-forwarding range
  target_tags   = ["coffee-db"]
}

resource "google_compute_firewall" "coffee_allow_run_to_db" {
  name      = "coffee-allow-run-to-db"
  network   = google_compute_network.coffee_vpc.id
  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["1521"]
  }

  # Cloud Run Direct VPC egress range + Cloud Build private-pool peering range.
  source_ranges = ["10.10.1.0/24", "10.30.0.0/24"]
  target_tags   = ["coffee-db"]
}
