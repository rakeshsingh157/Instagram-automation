import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://")

# PyMySQL does not support 'ssl-mode' as a query parameter, we provide ssl dict explicitly
db_url = db_url.replace("?ssl-mode=REQUIRED", "").replace("&ssl-mode=REQUIRED", "")

connect_args = {}

# Handle MySQL with SSL CA
if settings.DB_SSL_CA:
    ca_path = os.path.join(os.getcwd(), "ca.pem")
    if not os.path.exists(ca_path):
        with open(ca_path, "w") as f:
            # Clean up the multiline string formatting if it has extra quotes
            ca_content = settings.DB_SSL_CA.strip('"').replace('\\n', '\n')
            f.write(ca_content)
    connect_args["ssl"] = {"ca": ca_path}

engine = create_engine(db_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
