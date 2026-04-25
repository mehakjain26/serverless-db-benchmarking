resource "awscc_dsql_cluster" "dsql" {
  deletion_protection_enabled = false # Set to true for production
}

resource "aws_iam_policy" "lambda_dsql_policy" {
  name        = "lambda-dsql-access-policy"
  description = "Allows Lambda to connect to the DSQL cluster"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   =  ["dsql:ReadData","dsql:Connect","dsql:DbConnectAdmin"]
        Resource = awscc_dsql_cluster.dsql.resource_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_dsql_attachment" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_dsql_policy.arn
}

resource "aws_lambda_function" "lambda_dsql" {
  filename         = "lambda_function_dsql.zip"
  function_name    = "dsql-lambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function_dsql.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120
  environment {
    variables = {
      DSQL_ENDPOINT = awscc_dsql_cluster.dsql.endpoint
      DB_REGION     = var.aws_region
    }
  }
  source_code_hash = filebase64sha256("lambda_function_dsql.zip")
  depends_on = [awscc_dsql_cluster.dsql]
}
