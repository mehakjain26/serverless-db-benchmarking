resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "private" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 2)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
}

resource "aws_security_group" "lambda" {
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Data Sources (Required for IAM and Networking) ---
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {}

resource "aws_security_group" "db" {
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id] # Allow traffic from Lambda SG
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "main-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

import {
  to = aws_rds_cluster.aurora
  id = "free-tier-aurora"
}

import {
  to = aws_rds_cluster_instance.aurora_instance
  id = "free-tier-aurora-instance-1"
}


resource "aws_rds_cluster" "aurora" {
  cluster_identifier = "free-tier-aurora"
  engine             = "aurora-postgresql"
  engine_version     = "17.7"
  master_username    = "postgres"
  iam_database_authentication_enabled = true
  skip_final_snapshot = true

  lifecycle {
    ignore_changes = [master_password, availability_zones]
  }
}

resource "aws_rds_cluster_instance" "aurora_instance" {
  identifier         = "free-tier-aurora-instance-1"
  cluster_identifier = aws_rds_cluster.aurora.id
  engine             = "aurora-postgresql"
  engine_version     = "17.7"
  instance_class     = "db.serverless"
  promotion_tier     = 1
}

# --- Lambda Function ---
resource "aws_lambda_function" "lambda_rds" {
  filename         = "lambda_function_rds.zip"
  function_name    = "aurora-lambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function_rds.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120

  environment {
    variables = {
      AURORA_ENDPOINT = aws_rds_cluster.aurora.endpoint
      DB_REGION       = var.aws_region
      DB_NAME         = "postgres"
      DB_USER         = "postgres"
    }
  }
  source_code_hash = filebase64sha256("lambda_function_rds.zip")
  depends_on = [aws_rds_cluster.aurora]
}

# --- IAM Policy for Aurora Connection ---
resource "aws_iam_role_policy" "lambda_aurora_iam" {
  name = "lambda-aurora-iam-auth"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "rds-db:connect"
        Effect = "Allow"
        Resource = "arn:aws:rds-db:${var.aws_region}:${data.aws_caller_identity.current.account_id}:dbuser:${aws_rds_cluster.aurora.cluster_resource_id}/postgres"
      }
    ]
  })
}
resource "aws_lambda_function_url" "lambda_rds_url" {
  function_name      = aws_lambda_function.lambda_rds.function_name
  authorization_type = "NONE"
}
