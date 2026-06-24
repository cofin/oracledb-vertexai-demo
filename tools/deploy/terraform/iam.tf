# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# --- Cloud Run runtime service account -------------------------------------
resource "google_service_account" "coffee_run_sa" {
  account_id   = "coffee-run-sa"
  display_name = "Cymbal Coffee Cloud Run runtime SA"
}

resource "google_project_iam_member" "run_sa_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.coffee_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "run_sa_secret_accessor" {
  secret_id = google_secret_manager_secret.coffee_db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.coffee_run_sa.email}"
}

# --- Cloud Build deploy service account (NO Vertex) ------------------------
resource "google_service_account" "coffee_build_sa" {
  account_id   = "coffee-build-sa"
  display_name = "Cymbal Coffee Cloud Build deploy SA"
}

resource "google_project_iam_member" "build_sa_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.coffee_build_sa.email}"
}

# Lets the build SA deploy a service that RUNS AS coffee-run-sa.
resource "google_project_iam_member" "build_sa_act_as" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.coffee_build_sa.email}"
}

resource "google_project_iam_member" "build_sa_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.coffee_build_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "build_sa_secret_accessor" {
  secret_id = google_secret_manager_secret.coffee_db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.coffee_build_sa.email}"
}
