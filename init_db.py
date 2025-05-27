from database import create_tables, engine, Base
from sqlalchemy import text, inspect

def init_db():
    """Initialize the database with required tables"""
    try:
        print("Starting database initialization...")
        
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        print(f"Existing tables: {existing_tables}")
        
        # Create all tables
        print("Creating tables...")
        create_tables()
        
        # Verify tables were created
        tables_after = inspector.get_table_names()
        print(f"Tables after creation: {tables_after}")
        
        # Create indexes for better performance
        print("Creating indexes...")
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_price_alerts_product_id ON price_alerts(product_id)"))
            conn.commit()
        
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise e

if __name__ == "__main__":
    init_db() 