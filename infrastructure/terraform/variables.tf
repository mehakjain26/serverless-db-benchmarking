variable "aws_region" {
  description = "AWS region to deploy resources in."
  type        = string
  default     = "us-east-1"
}

variable "ibmcloud_api_key" {
  description = "IBM Cloud API Key for provisioning cloud resources."
  type        = string
  sensitive   = true
  default     = ""
}

# --- Neon Database Variables ---
variable "neon_host" {
  description = "Neon Serverless PostgreSQL host."
  type        = string
  default     = "ep-aged-snow-a4rg0q1j-pooler.us-east-1.aws.neon.tech"
}

variable "neon_db" {
  description = "Neon Serverless PostgreSQL database name."
  type        = string
  default     = "neondb"
}

variable "neon_user" {
  description = "Neon Serverless PostgreSQL user."
  type        = string
  default     = "neondb_owner"
}

variable "neon_password" {
  description = "Neon Serverless PostgreSQL password."
  type        = string
  sensitive   = true
  default     = ""
}

# --- MongoDB Variables ---
variable "mongo_uri" {
  description = "MongoDB connection URI."
  type        = string
  sensitive   = true
  default     = ""
}

# --- IBM Cloudant Variables ---
variable "cloudant_url" {
  description = "IBM Cloudant URL."
  type        = string
  default     = "https://c078c512-de59-4236-8ebf-39f311b26cae-bluemix.cloudantnosqldb.appdomain.cloud"
}

variable "cloudant_apikey" {
  description = "IBM Cloudant API Key."
  type        = string
  sensitive   = true
  default     = ""
}

variable "cloudant_db" {
  description = "IBM Cloudant database name."
  type        = string
  default     = "gtfs"
}
