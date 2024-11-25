from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configurar o banco de dados
Base = declarative_base()
engine = create_engine('sqlite:///dbCoffee.db')
Session = sessionmaker(bind=engine)
session = Session()