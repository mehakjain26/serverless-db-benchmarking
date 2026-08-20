# --- Discovery: Account IDs ---
data "aws_caller_identity" "current" {} # Account A (Lambda)

data "aws_caller_identity" "dynamo_acc" {
  provider = aws.dynamo_acc # Account B (DynamoDB)
}

# --- 7. AWS DynamoDB Table (Account B) ---
resource "aws_dynamodb_table" "gtfs_table" {
  provider       = aws.dynamo_acc
  name           = "gtfs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute { name = "pk"; type = "S" }
  attribute { name = "sk"; type = "S" }
  attribute { name = "stop_pk"; type = "S" }
  attribute { name = "departure_time"; type = "S" }
  attribute { name = "trip_pk"; type = "S" }

  global_secondary_index {
    name               = "gsi_stop_departure"
    hash_key           = "stop_pk"
    range_key          = "departure_time"
    projection_type    = "ALL"
  }

  global_secondary_index {
    name               = "gsi_trip"
    hash_key           = "trip_pk"
    range_key          = "sk"
    projection_type    = "ALL"
  }
}

# Resource Policy in Account B allowing Account A's Lambda Role
resource "aws_dynamodb_resource_policy" "cross_account" {
  provider     = aws.dynamo_acc
  resource_arn = aws_dynamodb_table.gtfs_table.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowCrossAccountLambda"
      Effect = "Allow"
      Principal = {
        AWS = aws_iam_role.lambda_exec.arn # ARNs are global
      }
      Action = [
        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
        "dynamodb:Query", "dynamodb:Scan", "dynamodb:BatchWriteItem"
      ]
      Resource = [
        aws_dynamodb_table.gtfs_table.arn,
        "${aws_dynamodb_table.gtfs_table.arn}/index/*"
      ]
    }]
  })
}

# --- Lambda for DynamoDB (Account A) ---
resource "aws_lambda_function" "lambda_dynamo" {
  filename         = "lambda_function_dynamo.zip"
  function_name    = "dynamo-lambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function_dynamo.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120

  environment {
    variables = {
      # Use the FULL ARN for cross-account access
      DYNAMO_TABLE = aws_dynamodb_table.gtfs_table.arn
    }
  }

  source_code_hash = fileexists("lambda_function_dynamo.zip") ? filebase64sha256("lambda_function_dynamo.zip") : ""
}

# IAM Policy in Account A allowing access to Account B's table
resource "aws_iam_role_policy" "lambda_dynamo_policy" {
  name = "lambda-dynamo-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchWriteItem"
        ]
      Effect   = "Allow"
      Resource = [
        aws_dynamodb_table.gtfs_table.arn,
        "${aws_dynamodb_table.gtfs_table.arn}/index/*"
      ]
    }]
  })
}

resource "aws_lambda_function_url" "lambda_dynamo_url" {
  function_name      = aws_lambda_function.lambda_dynamo.function_name
  authorization_type = "NONE"
}

output "lambda_dynamo_function_url" {
  value = aws_lambda_function_url.lambda_dynamo_url.function_url
}
