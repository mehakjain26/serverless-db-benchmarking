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
      allocation_mb = 2048 # 2GB
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
      CLOUDANT_APIKEY = "JjKdiiC57TeQuW3ymUe-CFyQSumbNBYDYGr-Cddv0FNa"
      CLOUDANT_URL    = "https://41d4f0e7-8673-4ce6-998c-3906c7106fea-bluemix.cloudantnosqldb.appdomain.cloud"
    }
  }

  source_code_hash = fileexists("lambda_function_cloudant.zip") ? filebase64sha256("lambda_function_cloudant.zip") : ""
}
