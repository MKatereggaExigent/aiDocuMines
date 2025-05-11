# Create a directory for SSL certificates
mkdir -p ssl

# Generate a private key
openssl genrsa -out ssl/server.key 2048

# Secure the key (PostgreSQL requires this)
chmod 600 ssl/server.key

# Generate a self-signed certificate valid for 1 year
openssl req -new -x509 -key ssl/server.key -out ssl/server.crt -days 365 -subj "/CN=postgresql"

# Generate a Certificate Authority (CA) file (optional)
cp ssl/server.crt ssl/ca-cert.pem

