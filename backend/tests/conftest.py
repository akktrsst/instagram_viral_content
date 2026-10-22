import os

# Keep tests off real services: no startup recovery against the configured database.
os.environ["APP_ENV"] = "test"
