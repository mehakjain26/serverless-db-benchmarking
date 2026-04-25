#!/bin/bash
set -e

# This script packages the Lambda function with psycopg2 for AWS Lambda
# Run this from the aws-lambda-rds-proxy-example directory

LAMBDA_DIR="lambda_build"
ZIP_FILE="lambda_function_rds.zip"

# Clean up any previous build
rm -rf "$LAMBDA_DIR" "$ZIP_FILE"
mkdir "$LAMBDA_DIR"

# Copy lambda_function.py
cp lambda_function_rds.py "$LAMBDA_DIR/"

# Install aurora-dsql-psycopg2 into the build directory
pip3 install --platform manylinux2014_x86_64 --target "$LAMBDA_DIR" --implementation cp --python-version 3.12 --only-binary=:all: aurora-dsql-python-connector
pip3 install --platform manylinux2014_x86_64 --target "$LAMBDA_DIR" --implementation cp --python-version 3.12 --only-binary=:all: psycopg2-binary

# Zip everything
cd "$LAMBDA_DIR"
zip -r9 "../$ZIP_FILE" .
cd ..

# Clean up build directory
rm -rf "$LAMBDA_DIR"

echo "Packaged $ZIP_FILE for Lambda deployment."