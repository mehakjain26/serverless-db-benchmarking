# --- 8. Neon PostgreSQL Lambda ---
resource "aws_lambda_function" "lambda_neon" {
  filename         = "lambda_function_neon.zip"
  function_name    = "neon-lambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function_neon.lambda_handler"
  runtime          = "python3.12"
  timeout          = 60

  environment {
    variables = {
      NEON_HOST             = "ep-aged-snow-a4rg0q1j-pooler.us-east-1.aws.neon.tech"
      NEON_DB               = "neondb"
      NEON_USER             = "neondb_owner"
      NEON_PASSWORD         = "npg_Is6KVvmAq8xh"
      NEON_SSLMODE          = "require"
    }
  }

  # This allows terraform to detect if the zip file changed
  source_code_hash = fileexists("lambda_function_neon.zip") ? filebase64sha256("lambda_function_neon.zip") : ""
}

resource "aws_lambda_function_url" "lambda_neon_url" {
  function_name      = aws_lambda_function.lambda_neon.function_name
  authorization_type = "NONE"
}

output "lambda_neon_function_url" {
  value = aws_lambda_function_url.lambda_neon_url.function_url
}
