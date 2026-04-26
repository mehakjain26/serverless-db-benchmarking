output "dsql_cluster_endpoint" {
  value = awscc_dsql_cluster.dsql.endpoint
}

output "aurora_endpoint" {
  value = aws_rds_cluster.aurora.endpoint
}

output "lambda_rds_function_url" {
  value = aws_lambda_function_url.lambda_rds_url.function_url
}
