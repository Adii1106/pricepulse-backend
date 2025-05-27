from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import uvicorn
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from database import get_db, Product, PriceHistory, PriceAlert, User
from scraper.amazon_scraper import AmazonScraper
from services.email_service import EmailService
from jose import JWTError, jwt
import hashlib
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="PricePulse API")

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    try:
        # Initialize database
        logger.info("Initializing database...")
        # Your database initialization code here
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ProductBase(BaseModel):
    url: HttpUrl
    target_price: Optional[float] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    name: str
    current_price: float
    image_url: Optional[str]
    created_at: datetime
    last_updated: datetime

    class Config:
        orm_mode = True

# Initialize services
scheduler = BackgroundScheduler()
scheduler.start()
amazon_scraper = AmazonScraper()
email_service = EmailService()

# Authentication functions
def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# Routes
@app.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        print(f"Attempting to register user: {user.email}")
        print(f"User data: {user.dict()}")
        
        # Check if user already exists
        db_user = db.query(User).filter(User.email == user.email).first()
        if db_user:
            print(f"Email {user.email} already registered")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = get_password_hash(user.password)
        print(f"Creating new user with email: {user.email}")
        print(f"Hashed password length: {len(hashed_password)}")
        
        try:
            db_user = User(
                email=user.email,
                username=user.username,
                hashed_password=hashed_password,
                is_active=True,
                created_at=datetime.utcnow()
            )
            print("User object created successfully")
            print(f"User object: {db_user.__dict__}")
        except Exception as e:
            print(f"Error creating user object: {str(e)}")
            print(f"Error type: {type(e)}")
            raise
        
        try:
            print("Adding user to database...")
            db.add(db_user)
            db.commit()
            print("User added to database successfully")
        except Exception as e:
            print(f"Error adding user to database: {str(e)}")
            print(f"Error type: {type(e)}")
            db.rollback()
            raise
        
        try:
            db.refresh(db_user)
            print(f"Successfully registered user: {user.email}")
            print(f"User after refresh: {db_user.__dict__}")
            
            # Return user data without sensitive information
            return {
                "id": db_user.id,
                "email": db_user.email,
                "username": db_user.username,
                "is_active": db_user.is_active
            }
        except Exception as e:
            print(f"Error refreshing user object: {str(e)}")
            print(f"Error type: {type(e)}")
            raise
        
    except Exception as e:
        print(f"Error during registration: {str(e)}")
        print(f"Error type: {type(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/products/", response_model=ProductResponse)
async def add_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Scrape initial product data
    product_data = await amazon_scraper.scrape_product(str(product.url))
    if not product_data["name"] or not product_data["price"]:
        raise HTTPException(status_code=400, detail="Could not fetch product information")
    
    # Create product in database
    db_product = Product(
        url=str(product.url),
        name=product_data["name"],
        current_price=float(product_data["price"]),
        target_price=product.target_price,
        image_url=product_data["image_url"],
        user_id=current_user.id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Add initial price history
    price_history = PriceHistory(
        product_id=db_product.id,
        price=float(product_data["price"])
    )
    db.add(price_history)
    db.commit()
    
    # Schedule price tracking
    scheduler.add_job(
        track_price,
        IntervalTrigger(minutes=30),
        args=[db_product.id],
        id=f"track_{db_product.id}"
    )
    
    return db_product

@app.get("/products/", response_model=List[ProductResponse])
async def list_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Product).filter(Product.user_id == current_user.id).all()

@app.get("/products/{product_id}", response_model=dict)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    price_history = db.query(PriceHistory).filter(
        PriceHistory.product_id == product_id
    ).order_by(PriceHistory.timestamp.desc()).all()
    
    return {
        "product": product,
        "price_history": price_history
    }

@app.get("/users/me", response_model=UserResponse)
async def get_current_user_data(current_user: User = Depends(get_current_user)):
    return current_user

@app.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Find the product and verify ownership
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.user_id == current_user.id
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Remove the scheduled job if it exists
        try:
            scheduler.remove_job(f"track_{product_id}")
        except:
            pass  # Ignore if job doesn't exist
        
        # Delete associated price history and alerts
        db.query(PriceHistory).filter(PriceHistory.product_id == product_id).delete()
        db.query(PriceAlert).filter(PriceAlert.product_id == product_id).delete()
        
        # Delete the product
        db.delete(product)
        db.commit()
        
        return {"message": "Product deleted successfully"}
    except Exception as e:
        db.rollback()
        print(f"Error deleting product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def track_price(product_id: int):
    """Track price for a product"""
    db = next(get_db())
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return
        
        # Scrape current price
        product_data = await amazon_scraper.scrape_product(product.url)
        if not product_data["price"]:
            return
        
        current_price = float(product_data["price"])
        
        # Update product price
        product.current_price = current_price
        product.last_updated = datetime.utcnow()
        
        # Add price history
        price_history = PriceHistory(
            product_id=product_id,
            price=current_price
        )
        db.add(price_history)
        
        # Check for price alerts
        if (product.target_price and 
            product.email and 
            current_price <= product.target_price):
            
            # Check if alert was already sent
            existing_alert = db.query(PriceAlert).filter(
                PriceAlert.product_id == product_id,
                PriceAlert.is_triggered == True
            ).first()
            
            if not existing_alert:
                # Send email alert
                email_service.send_price_alert(
                    to_email=product.email,
                    product_name=product.name,
                    current_price=current_price,
                    target_price=product.target_price,
                    product_url=product.url,
                    image_url=product.image_url
                )
                
                # Create alert record
                alert = PriceAlert(
                    product_id=product_id,
                    target_price=product.target_price,
                    email=product.email,
                    is_triggered=True
                )
                db.add(alert)
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Error tracking price for product {product_id}: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 