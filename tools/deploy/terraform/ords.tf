# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Service Account dedicated for ORDS Cloud Run service
resource "google_service_account" "coffee_ords_sa" {
  account_id   = "coffee-ords-sa"
  display_name = "Cymbal Coffee ORDS service SA"
}

# Grant the ORDS SA Secret Manager secret accessor role on the DB SYS password
resource "google_secret_manager_secret_iam_member" "ords_sa_system_secret_accessor" {
  secret_id = google_secret_manager_secret.coffee_db_system_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.coffee_ords_sa.email}"
}

# Grant the Cloud Build SA secret accessor role on the DB SYS password (required for config pipeline)
resource "google_secret_manager_secret_iam_member" "build_sa_system_secret_accessor" {
  secret_id = google_secret_manager_secret.coffee_db_system_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.coffee_build_sa.email}"
}

# Cloud Run service for ORDS
resource "google_cloud_run_v2_service" "coffee_ords" {
  name                = "coffee-ords"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account       = google_service_account.coffee_ords_sa.email
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

    # Direct VPC egress into coffee-vpc / coffee-run-subnet
    vpc_access {
      network_interfaces {
        network    = google_compute_network.coffee_vpc.id
        subnetwork = google_compute_subnetwork.coffee_run_subnet.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      # Bootstrap image; real image is set by cloudbuild deployment pipeline
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      env {
        name  = "DBHOST"
        value = "10.10.0.10"
      }
      env {
        name  = "DBPORT"
        value = "1521"
      }
      env {
        name  = "DBSERVICENAME"
        value = "freepdb1"
      }
      env {
        name = "ORACLE_PWD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.coffee_db_system_password.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  # Prevent Terraform from reverting changes made by the deployment pipeline
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_secret_manager_secret_version.coffee_db_system_password,
    google_secret_manager_secret_iam_member.ords_sa_system_secret_accessor,
  ]
}

# Allow unauthenticated invocation of the ORDS service for APEX URLs
resource "google_cloud_run_v2_service_iam_member" "coffee_ords_public" {
  name     = google_cloud_run_v2_service.coffee_ords.name
  location = google_cloud_run_v2_service.coffee_ords.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Output the Cloud Run service URL
output "coffee_ords_url" {
  description = "Public URL of the ORDS Cloud Run service."
  value       = google_cloud_run_v2_service.coffee_ords.uri
}
