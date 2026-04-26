#!/bin/bash
set -e

# Cleanup
rm -f lambda_function_dynamo.zip
rm -rf package_dynamo
mkdir -p package_dynamo

# Install base dependencies (excluding boto3 to save space)
pip3 install \
    --platform manylinux2014_x86_64 \
    --target=package_dynamo \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    numpy rich

# Copy the lambda code and shared logic
cp lambda_function_dynamo.py package_dynamo/
cp ../req_gen.py package_dynamo/
cp ../globals.py package_dynamo/
cp -r ../server package_dynamo/
cp -r ../dynamodb package_dynamo/

# Zip everything
cd package_dynamo
zip -r ../lambda_function_dynamo.zip .
cd ..

rm -rf package_dynamo

echo "✅ Package created: lambda_function_dynamo.zip"
