output "api_url" { value = "https://${var.staging_hostname}" }
output "load_balancer_dns" { value = aws_lb.api.dns_name }
output "database_endpoint" { value = aws_db_instance.postgres.address; sensitive = true }
output "evidence_bucket" { value = aws_s3_bucket.evidence.bucket }
output "receipt_kms_key_id" { value = aws_kms_key.receipts.arn }
output "github_deploy_role_arn" { value = aws_iam_role.github_deploy.arn }
output "migrator_task_definition" { value = aws_ecs_task_definition.migrator.arn }
output "private_subnet_ids" { value = aws_subnet.private[*].id }
output "api_security_group_id" { value = aws_security_group.api.id }
