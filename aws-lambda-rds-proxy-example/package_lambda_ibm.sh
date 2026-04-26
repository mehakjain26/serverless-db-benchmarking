#!/bin/bash
set -e

# Cleanup old zip
rm -f lambda_function_ibm.zip

# Create a temporary directory for packaging
mkdir -p package_ibm

# Install dependencies for Linux (Lambda's OS)
# We use psycopg2-binary because it includes the necessary C libraries
pip3 install \
    --platform manylinux2014_x86_64 \
    --target=package_ibm \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    psycopg2-binary
pip3 install \
    --platform manylinux2014_x86_64 \
    --target=package_ibm \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    numpy
pip3 install \
    --platform manylinux2014_x86_64 \
    --target=package_ibm \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    rich markdown-it-py pygments mdurl
pip3 install \
    --platform manylinux2014_x86_64 \
    --target=package_ibm \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    boto3

# Copy the lambda code and certificate
cp lambda_function_ibm.py package_ibm/
cp scripts_ibm/ibm_postgres_ca.crt package_ibm/
cp ../req_gen.py package_ibm/
cp ../globals.py package_ibm/
cp -r ../server package_ibm/

# Zip everything inside the package folder
cd package_ibm
zip -r ../lambda_function_ibm.zip .
cd ..

rm -rf package_ibm

echo "✅ Package created: lambda_function_ibm.zip (optimized for AWS Lambda Linux)"
