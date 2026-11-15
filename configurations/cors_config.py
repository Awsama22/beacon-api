from configurations.environment_config import environment

cors_options = {
    "allow_origins": [origin.strip() for origin in environment.CORS_ALLOWED_ORIGINS.split(",")],
    "allow_methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "X-Admin-Key"],
}
