from dotenv import load_dotenv, find_dotenv
import os

dotenv_file = find_dotenv()
print("Loading:", dotenv_file)

load_dotenv(dotenv_file)

print("DATABASE_URL =", repr(os.getenv("DATABASE_URL")))
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
from app.utils.email_utils import load_allowed_emails
from app.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_initial_users():
    db = SessionLocal()
    try:
        allowed_emails = load_allowed_emails("app/scripts/female_emails.csv")
        existing_emails = {user.email_id for user in db.query(User.email_id).all()}
        
        new_users = [User(email_id=email, is_active=False, is_verified=False) for email in allowed_emails if email not in existing_emails]
        
        if new_users:
            db.add_all(new_users)
            db.commit()
    except Exception as e:
        logger.error(f"Error seeding initial users: {e}")
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
        seed_initial_users()
    except Exception as e:
        logger.error(f"An error occurred during startup: {e}")
    yield
    # Code to run on shutdown
    logger.info("Application shutdown.")

app = FastAPI(lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
origins = [origin.strip() for origin in origins if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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
