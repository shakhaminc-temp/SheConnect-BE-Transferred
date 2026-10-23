from dotenv import load_dotenv, find_dotenv
import os

dotenv_file = find_dotenv()
load_dotenv(dotenv_file)
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.chat import router as chat_router
from app.routers.blog import router as blog_router
from sqlalchemy import text

from app.core.database import engine, Base, SessionLocal
from app.routers.auth import router as auth_router
from app.routers.travel import router as travel_router
from app.routers.geo import router as geo_router
from app.routers.emergency_contact import router as emergency_contact_router
from app.routers.connect import router as connect_router
from app.routers.carpool import router as carpool_router
from app.utils.email_utils import load_allowed_emails, load_colleges_from_csv
from app.models import User, College
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_initial_data():
    db = SessionLocal()
    try:
        csv_path = os.path.join(os.path.dirname(__file__), "scripts", "female_emails.csv")

        # 1. Sync Colleges from female_emails.csv
        csv_colleges = load_colleges_from_csv(csv_path)
        existing_colleges = {c.college_name for c in db.query(College.college_name).all()}
        
        new_colleges = [College(college_name=name) for name in csv_colleges if name not in existing_colleges]
        if new_colleges:
            db.add_all(new_colleges)
            db.commit()

        # 2. Sync Allowed Users from female_emails.csv
        allowed_emails = load_allowed_emails(csv_path)
        existing_emails = {user.email_id.lower() for user in db.query(User.email_id).all() if user.email_id}
        
        new_users = [User(email_id=email, is_active=False, is_verified=False) for email in allowed_emails if email not in existing_emails]
        if new_users:
            db.add_all(new_users)
            db.commit()

    except Exception as e:
        logger.error(f"Error seeding initial data: {e}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    try:
        with engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            connection.commit()
        Base.metadata.create_all(bind=engine)
        seed_initial_data()
    except Exception as e:
        logger.error(f"An error occurred during startup: {e}")
    yield
    # Code to run on shutdown
    logger.info("Application shutdown.")

app = FastAPI(lifespan=lifespan)

origins_env = os.getenv("CORS_ORIGINS", "*")
if origins_env.strip() == "*":
    origins = ["*"]
else:
    origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True if origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(travel_router)
app.include_router(geo_router)
app.include_router(chat_router)
app.include_router(blog_router)
app.include_router(connect_router)
app.include_router(emergency_contact_router)
app.include_router(carpool_router)

@app.get("/")
def home():
    return {"message": "Backend is running"}
