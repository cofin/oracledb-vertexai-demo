# Secret Manager secrets for Cymbal Coffee Oracle DB.
# These are referenced by the DB VM and will be consumed by the Cloud Run service / build pool in Chapter 3.

resource "google_secret_manager_secret" "coffee_db_password" {
  secret_id = var.db_password_secret_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "coffee_db_password" {
  secret      = google_secret_manager_secret.coffee_db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "coffee_db_system_password" {
  secret_id = var.system_password_secret_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "coffee_db_system_password" {
  secret      = google_secret_manager_secret.coffee_db_system_password.id
  secret_data = var.db_system_password
}
