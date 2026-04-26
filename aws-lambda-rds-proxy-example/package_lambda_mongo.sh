#!/bin/bash
set -e

# Cleanup
rm -f lambda_function_mongo.zip
rm -rf package_mongo
mkdir -p package_mongo

# Install dependencies for Linux (Lambda's OS)
# We MUST include dnspython for mongodb+srv support
pip3 install \
    --platform manylinux2014_x86_64 \
    --target=package_mongo \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    pymongo dnspython numpy rich boto3

# Copy the lambda code and shared logic
cp lambda_function_mongo.py package_mongo/
cp ../req_gen.py package_mongo/
cp ../globals.py package_mongo/
cp -r ../server package_mongo/

# Zip everything
cd package_mongo
zip -r ../lambda_function_mongo.zip .
cd ..

rm -rf package_mongo

echo "✅ Package created: lambda_function_mongo.zip"
