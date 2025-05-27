from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv
from sqlalchemy import inspect

load_dotenv()

# Get the absolute path to the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'pricepulse.db')}"

print(f"Database URL: {DATABASE_URL}")

# Create SQLAlchemy engine with echo=True for debugging
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    products = relationship("Product", back_populates="user")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    name = Column(String)
    current_price = Column(Float)
    target_price = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    user = relationship("User", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product")
    price_alerts = relationship("PriceAlert", back_populates="product")

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="price_history")

class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    target_price = Column(Float)
    email = Column(String)
    is_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="price_alerts")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    print("Starting database initialization...")
    try:
        # Drop all existing tables
        print("Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("Existing tables dropped successfully")
        
        # Create all tables
        print("Creating new tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully")
        
        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Created tables: {tables}")
        
        # Create indexes
        print("Creating indexes...")
        for table_name in tables:
            indexes = inspector.get_indexes(table_name)
            print(f"Indexes for {table_name}: {indexes}")
        
        print("Database initialization completed successfully!")
    except Exception as e:
        print(f"Error during database initialization: {str(e)}")
        print(f"Error type: {type(e)}")
        raise 