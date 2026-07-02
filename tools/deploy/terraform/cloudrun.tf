# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Cloud Run service. Terraform creates it with a bootstrap "hello" image and
# ignores subsequent image changes; cloudbuild's `gcloud run deploy` swaps in
# the real coffee-app:$SHORT_SHA image on every deploy.
resource "google_cloud_run_v2_service" "coffee_app" {
  name                = "coffee-app"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account       = google_service_account.coffee_run_sa.email
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

    # Direct VPC egress into coffee-vpc / coffee-run-subnet.
    # PRIVATE_RANGES_ONLY: private IPs (the DB) go through the VPC; Google
    # APIs / Vertex still use the public path.
    vpc_access {
      network_interfaces {
        network    = google_compute_network.coffee_vpc.id
        subnetwork = google_compute_subnetwork.coffee_run_subnet.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      # Bootstrap only; real image set by cloudbuild gcloud run deploy.
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      env {
        name  = "DATABASE_HOST"
        value = "10.10.0.10"
      }
      env {
        name  = "DATABASE_PORT"
        value = "1521"
      }
      env {
        name  = "DATABASE_SERVICE_NAME"
        value = "freepdb1"
      }
      env {
        name  = "DATABASE_USER"
        value = "app"
      }
      env {
        name  = "VERTEX_AI_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "VERTEX_AI_LOCATION"
        value = "us-central1"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }
      env {
        name  = "ORACLE_ADK_IN_MEMORY"
        value = "true"
      }
      env {
        name  = "ORACLE_LITESTAR_SESSION_IN_MEMORY"
        value = "true"
      }
      # Only the APP secret (coffee-db-password) reaches Cloud Run. The SYS
      # secret coffee-db-system-password is DB-VM-only and is never wired here.
      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.coffee_db_password.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  # cloudbuild owns the deployed image; Terraform must not revert it.
  # client/client_version are stamped by `gcloud run deploy`; ignore them too
  # or `terraform plan` shows a perpetual diff after the first pipeline deploy
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_secret_manager_secret_version.coffee_db_password,
    google_secret_manager_secret_iam_member.run_sa_secret_accessor,
  ]
}


# LAB ONLY: allow public (unauthenticated) access so the learner can open the
# URL. The cloudbuild deploy step also passes --allow-unauthenticated; this
# binding keeps Terraform and the pipeline consistent.
resource "google_cloud_run_v2_service_iam_member" "coffee_app_public" {
  name     = google_cloud_run_v2_service.coffee_app.name
  location = google_cloud_run_v2_service.coffee_app.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "coffee_app_url" {
  description = "Public URL of the Cloud Run service."
  value       = google_cloud_run_v2_service.coffee_app.uri
}
