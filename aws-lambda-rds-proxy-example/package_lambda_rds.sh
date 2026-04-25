#!/bin/bash
set -e

# This script packages the Lambda function with project dependencies and psycopg2 for AWS Lambda
# Run this from the project root directory

LAMBDA_DIR="aws_lambda_build"
ZIP_FILE="lambda_function_rds.zip"
SRC_DIR="aws-lambda-rds-proxy-example"

# Clean up any previous build
rm -rf "$LAMBDA_DIR" "$ZIP_FILE"
mkdir "$LAMBDA_DIR"

# Copy lambda_function.py from its specific directory
cp "$SRC_DIR/lambda_function_rds.py" "$LAMBDA_DIR/"

# Copy shared project dependencies from root
cp req_gen.py "$LAMBDA_DIR/"
cp globals.py "$LAMBDA_DIR/"
cp -r server "$LAMBDA_DIR/"

# Install dependencies into the build directory
# Note: we use manylinux2014_x86_64 to ensure the binary is compatible with AWS Lambda environment
# We target Python 3.12 as it's the current recommended Lambda runtime
pip3 install --platform manylinux2014_x86_64 --target "$LAMBDA_DIR" --implementation cp --python-version 3.12 --only-binary=:all: psycopg2-binary
pip3 install --platform manylinux2014_x86_64 --target "$LAMBDA_DIR" --implementation cp --python-version 3.12 --only-binary=:all: numpy
pip3 install --platform manylinux2014_x86_64 --target "$LAMBDA_DIR" --implementation cp --python-version 3.12 --only-binary=:all: rich markdown-it-py pygments mdurl
pip3 install --platform manylinux2014_x86_64 --target "$LAMBDA_DIR" --implementation cp --python-version 3.12 --only-binary=:all: boto3

# Zip everything
cd "$LAMBDA_DIR"
zip -r9 "../$ZIP_FILE" .
cd ..

# Clean up build directory
rm -rf "$LAMBDA_DIR"

echo "Packaged $ZIP_FILE for Lambda deployment."
echo "Zip contents: lambda_function_rds.py, req_gen.py, globals.py, server/ directory, and libraries."