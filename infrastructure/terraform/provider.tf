terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    awscc = {
      source  = "hashicorp/awscc"
      version = "~> 1.0"
    }
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 1.63.0"
    }
  }
  required_version = ">= 1.3.0"
}

provider "aws" {
  region = var.aws_region
}

provider "aws" {
  alias   = "dynamo_acc"
  region  = "us-east-1"
  profile = "bench-dynamo"
}

provider "ibm" {
  region           = "us-south"
  ibmcloud_api_key = var.ibmcloud_api_key
}