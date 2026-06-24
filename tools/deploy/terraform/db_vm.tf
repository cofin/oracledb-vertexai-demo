resource "google_compute_disk" "coffee_db_data" {
  name = "coffee-db-data"
  type = "pd-ssd"
  zone = var.zone
  size = var.db_data_disk_size_gb
}

resource "google_service_account" "coffee_db_sa" {
  account_id   = "coffee-db-sa"
  display_name = "Cymbal Coffee DB VM service account"
}

locals {
  cloud_init = templatefile("${path.module}/../gcp/cloud-init-oracle.yaml.tftpl", {
    app_user                  = "app"
    app_password_secret_id    = var.db_password_secret_id     # coffee-db-password (Ch3)
    system_password_secret_id = var.system_password_secret_id # coffee-db-system-password (Ch3)
    project_id                = var.project_id
    oracle_image              = "gvenzl/oracle-free:latest"
    init_vector_sql           = file("${path.module}/../../oracle/on_init/00_configure_vector_memory.sql")
    init_db_sql               = file("${path.module}/../../oracle/on_init/db_init.sql")
    startup_verify_sql        = file("${path.module}/../../oracle/on_startup/00_verify_vector_memory.sql")
    startup_test_sql          = file("${path.module}/../../oracle/on_startup/01_startup_test.sql")
  })
}

resource "google_compute_instance" "coffee_db" {
  name         = "coffee-db"
  machine_type = var.db_machine_type
  zone         = var.zone
  tags         = ["coffee-db"]

  # Standard (NOT Spot/preemptible) — this is the durable DB.
  scheduling {
    provisioning_model  = "STANDARD"
    preemptible         = false
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
  }

  boot_disk {
    initialize_params {
      image = "cos-cloud/${var.cos_image_family}"
      size  = 20
      type  = "pd-balanced"
    }
  }

  attached_disk {
    source      = google_compute_disk.coffee_db_data.id
    device_name = "coffee-db-data" # → /dev/disk/by-id/google-coffee-db-data
  }

  network_interface {
    subnetwork = google_compute_subnetwork.coffee_subnet.id
    network_ip = google_compute_address.coffee_db_ip.address
    # No access_config block => --no-address (no external IP).
  }

  service_account {
    email  = google_service_account.coffee_db_sa.email
    scopes = ["cloud-platform"] # required for the metadata-token Secret Manager read
  }

  metadata = {
    user-data                 = local.cloud_init
    google-logging-enabled    = "true"
    google-monitoring-enabled = "true"
  }

  # Boot only after BOTH secret VERSIONS exist (payloads, not just the secret
  # resources) and the IAM bindings are in place (Ch3 secrets.tf, same root).
  # Depending on the *versions* guarantees the boot-time fetch (FR11) finds a
  # payload rather than hitting the fail-loud empty-read path.
  depends_on = [
    google_secret_manager_secret_iam_member.db_sa_app_secret_access,
    google_secret_manager_secret_iam_member.db_sa_system_secret_access,
    google_secret_manager_secret_version.coffee_db_password,
    google_secret_manager_secret_version.coffee_db_system_password,
  ]
}

# Secrets + versions are created in Ch3 secrets.tf (same Terraform root).
# These bindings let the VM SA read both at boot.
resource "google_secret_manager_secret_iam_member" "db_sa_app_secret_access" {
  secret_id = google_secret_manager_secret.coffee_db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.coffee_db_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "db_sa_system_secret_access" {
  secret_id = google_secret_manager_secret.coffee_db_system_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.coffee_db_sa.email}"
}
