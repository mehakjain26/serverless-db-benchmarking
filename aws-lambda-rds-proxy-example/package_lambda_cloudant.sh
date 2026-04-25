#!/bin/bash
set -e

# Cleanup
rm -f lambda_function_cloudant.zip
rm -rf package_cloudant
mkdir -p package_cloudant

# Install dependencies for Linux (Lambda's OS)
pip3 install \
    --platform manylinux2014_x86_64 \
    --target=package_cloudant \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    ibmcloudant ibm-cloud-sdk-core

# Copy the lambda code
cp lambda_function_cloudant.py package_cloudant/

# Zip everything
cd package_cloudant
zip -r ../lambda_function_cloudant.zip .
cd ..

rm -rf package_cloudant

echo "✅ Package created: lambda_function_cloudant.zip"
