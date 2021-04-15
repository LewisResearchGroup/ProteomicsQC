#!/bin/bash

echo '' > .env
echo "SECRET_KEY='`openssl rand -hex 32`'" >> .env
echo "OIDC_RSA_PRIVATE_KEY='`openssl genrsa 4096`'" >> .env
