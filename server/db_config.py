POSTGRES = {
    "host": "b64fee03-6278-4279-8a82-c64e103dde88.brjdfmfw09op3teml03g.databases.appdomain.cloud",
    "port": 32301,
    "dbname": "ibmclouddb",
    "user": "ibm_cloud_8c47b8f6_d1cc_4c75_bf3d_8b6fd6629c63",
    "password": "CoUfNz5byZqA34HrMVER2WBAwYvQw0Kx",
    "sslmode": "verify-full",
    "sslrootcert": "ibm_postgres_ca.crt",
}

NEON = {
    "host": "ep-aged-snow-a4rg0q1j-pooler.us-east-1.aws.neon.tech",
    "dbname": "neondb",
    "user": "neondb_owner",
    "password": "npg_Is6KVvmAq8xh",
    "sslmode": "require",
    "channel_binding": "require",
}

POSTGRES_DBS = {"postgres": POSTGRES, "neon": NEON}


def get_postgres(name: str = "postgres") -> dict:
    if name not in POSTGRES_DBS:
        raise ValueError(f"Unknown db '{name}'. Choose from: {list(POSTGRES_DBS)}")
    return POSTGRES_DBS[name]


MONGO = {
    "uri": "mongodb+srv://dbUser:dbUserPassword@cluster0.orkddvx.mongodb.net/?appName=Cluster0",
    "db": "gtfs_data",
    "collection": "gtfs",
}

CLOUDANT = {
    "url": "https://c078c512-de59-4236-8ebf-39f311b26cae-bluemix.cloudantnosqldb.appdomain.cloud",
    "apikey": "suNVFvme59ieXqmRCTTJNaLeFenMzhj0YsrKca-in6Kc",
    "db": "gtfs",
}
