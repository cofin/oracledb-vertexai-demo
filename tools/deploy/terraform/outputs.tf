output "db_internal_ip" {
  value       = google_compute_address.coffee_db_ip.address
  description = "Static internal IP of the Oracle DB VM (DATABASE_HOST for Ch3)."
}

output "vpc_self_link" {
  value       = google_compute_network.coffee_vpc.self_link
  description = "Self-link of coffee-vpc (consumed by Ch3 Cloud Run + build pool)."
}

output "db_subnet_self_link" {
  value       = google_compute_subnetwork.coffee_subnet.self_link
  description = "Self-link of coffee-subnet (DB subnet)."
}

output "run_subnet_self_link" {
  value       = google_compute_subnetwork.coffee_run_subnet.self_link
  description = "Self-link of coffee-run-subnet (Cloud Run Direct VPC egress)."
}

output "db_target_tag" {
  value       = "coffee-db"
  description = "Network tag the firewall rules target."
}

output "db_service_account_email" {
  value       = google_service_account.coffee_db_sa.email
  description = "Email of the DB VM service account."
}
