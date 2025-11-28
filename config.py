# config.py
import os
# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-to-a-strong-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# Token expiry: keep both minutes and seconds for compatibility
ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
ACCESS_TOKEN_EXPIRES_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRES_SECONDS", str(ACCESS_TOKEN_EXPIRES_MINUTES * 60)))
REFRESH_TOKEN_EXPIRES_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRES_MINUTES", "1440"))  # default 24 hours
REFRESH_TOKEN_EXPIRES_SECONDS = int(os.getenv("REFRESH_TOKEN_EXPIRES_SECONDS", str(REFRESH_TOKEN_EXPIRES_MINUTES * 60)))
REFRESH_TOKEN_ROTATION = os.getenv("REFRESH_TOKEN_ROTATION", "True").lower() == "true"
# Mongo
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "authdb")
