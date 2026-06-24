# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Docker registry that holds the coffee-app image built by Cloud Build.
# Image path: ${var.region}-docker.pkg.dev/${var.project_id}/coffee-artifacts/coffee-app
resource "google_artifact_registry_repository" "coffee_artifacts" {
  location      = var.region
  repository_id = "coffee-artifacts"
  description   = "Cymbal Coffee app images (lab)."
  format        = "DOCKER"
}
