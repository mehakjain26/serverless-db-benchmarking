#!/bin/bash
set -e

# Cleanup
rm -f lambda_function_neon.zip
rm -rf package_neon
mkdir -p package_neon

# Install dependencies for Linux (Lambda's OS)
# We use psycopg2-binary for the easiest standalone setup in Lambda
pip3 install \
    --platform manylinux2014_x86_64 \
    --target=package_neon \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    psycopg2-binary numpy rich

# Copy the lambda code and shared logic
cp lambda_function_neon.py package_neon/
cp ../req_gen.py package_neon/
cp ../globals.py package_neon/
cp -r ../server package_neon/

# Zip everything
cd package_neon
zip -r ../lambda_function_neon.zip .
cd ..

rm -rf package_neon

echo "✅ Package created: lambda_function_neon.zip"
