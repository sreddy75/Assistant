import os
from sqlalchemy import create_engine, MetaData, Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

# Use environment variables for database connection details
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5532')
DB_NAME = os.getenv('DB_NAME', 'ai')
DB_USER = os.getenv('DB_USER', 'ai')
DB_PASS = os.getenv('DB_PASS', 'ai')

# Construct the database URL
db_url = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"Attempting to connect to: {db_url}")

Base = declarative_base()

# Define a dummy class to handle the Vector type
class DummyVector(Base):
    __tablename__ = 'dummy_vector'
    id = Column(Integer, primary_key=True)
    embedding = Column(Vector(1536))  # Adjust the dimension as needed

try:
    engine = create_engine(db_url)
    
    # Test the connection
    with engine.connect() as connection:
        print("Successfully connected to the database.")

    metadata = MetaData()
    metadata.reflect(bind=engine)

    print("\nCurrent Database Schema:")
    print("========================")

    for table_name, table in metadata.tables.items():
        print(f"\nTable: {table_name}")
        # Replace NullType columns with Vector
        for column in table.columns:
            if str(column.type) == 'NullType' and column.name == 'embedding':
                column.type = Vector(1536)  # Adjust the dimension as needed
        print(CreateTable(table).compile(engine))

except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()