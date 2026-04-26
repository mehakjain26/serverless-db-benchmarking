# --- 1. Resource Group ---
# Using a data source to get an existing resource group (usually "Default")
data "ibm_resource_group" "group" {
  name = "Default"
}

# --- 2. IBM Cloud Database for PostgreSQL ---
resource "ibm_database" "postgres" {
  resource_group_id = data.ibm_resource_group.group.id
  name              = "gtfs-ibm-postgres"
  service           = "databases-for-postgresql"
  plan              = "standard" # Minimum plan for most features
  location          = "us-south"

  # Configuration for Public Endpoint
  service_endpoints = "public"

  # Resource Allocation (Minimum settings)
  adminpassword = "YourSecurePassword123" # Ideally use a variable or secret
  
  group {
    group_id = "member"
    memory {
      allocation_mb = 8192 # 8GB
    }
    disk {
      allocation_mb = 5120 # 5GB
    }
    cpu {
      allocation_count = 3
    }
  }

  allowlist {
    address     = "0.0.0.0/0"
    description = "Allow all for initial setup"
  }
}

# --- 3. IAM Service Credential ---
# This creates a set of credentials (connection string) managed by IAM
resource "ibm_resource_key" "postgres_key" {
  name                 = "gtfs-ingest-key"
  resource_instance_id = ibm_database.postgres.id
  role                 = "Administrator"
}

# --- Outputs ---
output "postgres_connection_strings" {
  value     = ibm_resource_key.postgres_key.credentials
  sensitive = true # contains password
}

output "postgres_host" {
  value = ibm_database.postgres.connectionstrings[0].hosts[0].hostname
}

# --- 4. AWS Lambda connecting to IBM ---
resource "aws_lambda_function" "lambda_ibm" {
  filename         = "lambda_function_ibm.zip"
  function_name    = "ibm-postgres-lambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function_ibm.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120

  environment {
    variables = {
      IBM_DB_HOST     = ibm_database.postgres.connectionstrings[0].hosts[0].hostname
      IBM_DB_PORT     = ibm_database.postgres.connectionstrings[0].hosts[0].port
      IBM_DB_NAME     = "ibmclouddb"
      IBM_DB_USER     = ibm_resource_key.postgres_key.credentials["connection.postgres.authentication.username"]
      IBM_DB_PASSWORD = ibm_resource_key.postgres_key.credentials["connection.postgres.authentication.password"]
    }
  }

  # This ensures the zip is ready before terraform tries to upload it
  source_code_hash = fileexists("lambda_function_ibm.zip") ? filebase64sha256("lambda_function_ibm.zip") : ""
}

resource "aws_lambda_function_url" "lambda_ibm_url" {
  function_name      = aws_lambda_function.lambda_ibm.function_name
  authorization_type = "NONE"
}

output "lambda_ibm_function_url" {
  value = aws_lambda_function_url.lambda_ibm_url.function_url
}

# --- 5. AWS Lambda connecting to Cloudant ---
resource "aws_lambda_function" "lambda_cloudant" {
  filename         = "lambda_function_cloudant.zip"
  function_name    = "ibm-cloudant-lambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function_cloudant.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120

  environment {
    variables = {
      CLOUDANT_APIKEY = "suNVFvme59ieXqmRCTTJNaLeFenMzhj0YsrKca-in6Kc"
      CLOUDANT_URL    = "https://c078c512-de59-4236-8ebf-39f311b26cae-bluemix.cloudantnosqldb.appdomain.cloud"
      CLOUDANT_DB     = "gtfs"
    }
  }

  source_code_hash = fileexists("lambda_function_cloudant.zip") ? filebase64sha256("lambda_function_cloudant.zip") : ""
}

resource "aws_lambda_function_url" "lambda_cloudant_url" {
  function_name      = aws_lambda_function.lambda_cloudant.function_name
  authorization_type = "NONE"
}

output "lambda_cloudant_function_url" {
  value = aws_lambda_function_url.lambda_cloudant_url.function_url
}

# --- 6. AWS Lambda connecting to MongoDB ---
resource "aws_lambda_function" "lambda_mongo" {
  filename         = "lambda_function_mongo.zip"
  function_name    = "mongo-lambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function_mongo.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120

  environment {
    variables = {
      MONGO_URI = "mongodb+srv://dbUser:dbUserPassword@cluster0.orkddvx.mongodb.net/?appName=Cluster0"
    }
  }

  source_code_hash = fileexists("lambda_function_mongo.zip") ? filebase64sha256("lambda_function_mongo.zip") : ""
}

resource "aws_lambda_function_url" "lambda_mongo_url" {
  function_name      = aws_lambda_function.lambda_mongo.function_name
  authorization_type = "NONE"
}

output "lambda_mongo_function_url" {
  value = aws_lambda_function_url.lambda_mongo_url.function_url
}
