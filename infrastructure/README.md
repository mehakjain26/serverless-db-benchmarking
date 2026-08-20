# Serverless Infrastructure & Multi-Cloud Deployment Guide

This directory houses the **Infrastructure as Code (IaC)** files and AWS Lambda execution code used to deploy the serverless query layer for database benchmarking.

---

## 🏗️ Directory Layout

```
├── README.md               # Infrastructure documentation (this file)
├── terraform/              # Terraform configurations
│   ├── provider.tf         # Multi-cloud provider definitions (AWS, IBM)
│   ├── variables.tf        # Input variable declarations
│   ├── outputs.tf          # Output configuration (Lambda URLs)
│   ├── rds.tf              # AWS RDS / Serverless Aurora configurations
│   ├── dynamo.tf           # DynamoDB tables, indexes & Lambda role policies
│   ├── neon.tf             # Neon Postgres Lambda and integration details
│   ├── ibm_postgres.tf     # IBM Cloud PostgreSQL resource definitions
│   └── terraform.tfvars    # Environment variables
├── lambda/                 # AWS Lambda handlers (Python 3.12 runtime)
│   ├── lambda_function_dynamo.py
│   ├── lambda_function_mongo.py
│   ├── lambda_function_cloudant.py
│   ├── lambda_function_neon.py
│   ├── lambda_function_ibm.py
│   └── lambda_function_rds.py
└── scripts/                # Utility scripts to bundle Lambda archives
    ├── package_lambda_dynamo.sh
    ├── package_lambda_mongo.sh
    ├── package_lambda_cloudant.sh
    ├── package_lambda_neon.sh
    ├── package_lambda_ibm.sh
    └── package_lambda_rds.sh
```

---

## 🛠️ Step-by-Step Terraform Deployment

### 1. Prerequisites
- Install the [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (v1.3.0+).
- Configure your AWS credentials via local environment variables or standard AWS CLI profiles:
  ```bash
  export AWS_ACCESS_KEY_ID="your_access_key"
  export AWS_SECRET_ACCESS_KEY="your_secret_key"
  ```
- Ensure you have Python 3.12 installed locally to package Lambda function archives.

### 2. Package Lambda Archives
Before applying Terraform, you must package the Python functions into zip files expected by the Lambda resources. Run the packagers located in `scripts/`:
```bash
chmod +x infrastructure/scripts/*.sh
./infrastructure/scripts/package_lambda_dynamo.sh
./infrastructure/scripts/package_lambda_mongo.sh
./infrastructure/scripts/package_lambda_neon.sh
./infrastructure/scripts/package_lambda_ibm.sh
./infrastructure/scripts/package_lambda_rds.sh
```
This builds and places `*.zip` files directly under the `infrastructure/terraform/` directory.

### 3. Initialize Terraform
Navigate to the Terraform directory and initialize the cloud providers:
```bash
cd infrastructure/terraform
terraform init
```

### 4. Configure Variables
Copy and rename the tfvars template, then configure your custom credentials (e.g. IBM API key):
```bash
# Define your sensitive API keys and region settings in terraform.tfvars
ibmcloud_api_key = "your_ibm_cloud_api_key"
aws_region       = "us-east-1"
```

### 5. Apply Configurations
Verify the execution plan and deploy resources to the cloud:
```bash
terraform plan
terraform apply
```

### 6. Save Function URLs
Once deployment succeeds, Terraform outputs the public **Function URLs** for the deployed Lambdas:
```bash
Outputs:

lambda_dynamo_function_url = "https://squjzm5bmxt2ajq2ncxgoldjuq0kqmid.lambda-url.us-east-1.on.aws/"
lambda_mongo_function_url  = "https://w7th34c5pmhicjw2uauiz476ie0ovtkl.lambda-url.us-east-1.on.aws/"
lambda_neon_function_url   = "https://npefkdvgfzdxr6adqh43khhhuq0legzg.lambda-url.us-east-1.on.aws/"
```
Export these URLs into your local `.env` file to begin benchmarking in HTTP mode.
