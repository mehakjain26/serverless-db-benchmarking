import os
from pathlib import Path

# Optional load of python-dotenv for local development convenience
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Dynamically locate the IBM CA Certificate relative to this file
DEFAULT_CA_CERT = str(Path(__file__).parent / "ibm_postgres_ca.crt")

# IBM Cloud PostgreSQL (Relational DB) configuration mapping
POSTGRES = {
    "host": os.getenv("POSTGRES_HOST", "b64fee03-6278-4279-8a82-c64e103dde88.brjdfmfw09op3teml03g.databases.appdomain.cloud"),
    "port": int(os.getenv("POSTGRES_PORT", "32301")),
    "dbname": os.getenv("POSTGRES_DBNAME", "ibmclouddb"),
    "user": os.getenv("POSTGRES_USER", "ibm_cloud_8c47b8f6_d1cc_4c75_bf3d_8b6fd6629c63"),
    "password": os.getenv("POSTGRES_PASSWORD", ""), # Filled via environment configuration
    "sslmode": os.getenv("POSTGRES_SSLMODE", "verify-full"),
    "sslrootcert": os.getenv("POSTGRES_SSLROOTCERT", DEFAULT_CA_CERT),
}

# Neon Serverless PostgreSQL configuration mapping
NEON = {
    "host": os.getenv("NEON_HOST", "ep-aged-snow-a4rg0q1j-pooler.us-east-1.aws.neon.tech"),
    "dbname": os.getenv("NEON_DBNAME", "neondb"),
    "user": os.getenv("NEON_USER", "neondb_owner"),
    "password": os.getenv("NEON_PASSWORD", ""), # Filled via environment configuration
    "sslmode": os.getenv("NEON_SSLMODE", "require"),
    "channel_binding": "require",
}

POSTGRES_DBS = {"postgres": POSTGRES, "neon": NEON}


def get_postgres(name: str = "postgres") -> dict:
    """Returns database configuration parameters for a specified PostgreSQL target."""
    if name not in POSTGRES_DBS:
        raise ValueError(f"Unknown db '{name}'. Choose from: {list(POSTGRES_DBS)}")
    return POSTGRES_DBS[name]


# MongoDB Atlas (Document Store) configuration mapping
MONGO = {
    "uri": os.getenv("MONGO_URI", "mongodb+srv://dbUser:<password>@cluster0.orkddvx.mongodb.net/?appName=Cluster0"),
    "db": os.getenv("MONGO_DB", "gtfs_data"),
    "collection": os.getenv("MONGO_COLLECTION", "gtfs"),
}

# IBM Cloudant (Document Store) configuration mapping
CLOUDANT = {
    "url": os.getenv("CLOUDANT_URL", "https://c078c512-de59-4236-8ebf-39f311b26cae-bluemix.cloudantnosqldb.appdomain.cloud"),
    "apikey": os.getenv("CLOUDANT_APIKEY", ""), # Filled via environment configuration
    "db": os.getenv("CLOUDANT_DB", "gtfs"),
}
