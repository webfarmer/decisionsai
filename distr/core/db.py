from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
import os
from distr.core.constants import DB_DIR
from datetime import datetime

Base = declarative_base()

class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    language = Column(String)
    theme = Column(String)
    input_device = Column(String)
    output_device = Column(String)
    volume = Column(Integer)
    ai_model = Column(String)
    temperature = Column(Float)

class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('chats.id'), nullable=True)
    title = Column(String)
    input = Column(Text)
    response = Column(Text)
    params = Column(Text)  # Store as JSON string
    additional_context = Column(Text)
    image = Column(String)  # Store image path
    code = Column(Text)
    is_archived = Column(Boolean, default=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    children = relationship("Chat", 
                            backref=backref("parent", remote_side=[id]),
                            cascade="all, delete-orphan")

# Create the database file if it doesn't exist
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

db_path = os.path.join(DB_DIR, 'settings.db')
engine = create_engine(f'sqlite:///{db_path}')

# Create the table
Base.metadata.create_all(engine)

# Create a session factory
Session = sessionmaker(bind=engine)

def get_session():
    return Session()
