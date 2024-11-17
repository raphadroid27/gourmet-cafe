from sqlalchemy import create_engine, Column, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configurar o banco de dados
Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    email = Column(String, primary_key=True)
    nome = Column(String)
    senha = Column(String)
    codigo_recuperacao = Column(String)
    data_nascimento = Column(Date)
    endereco_entrega = Column(String)

class Produto(Base):
    __tablename__ = 'produtos'
    id = Column(String, primary_key=True)
    nome = Column(String)
    descricao = Column(String)
    preco = Column(Float)
    imagem = Column(String)
    tipo = Column(String)
    ingredientes = Column(String)

class Compra(Base):
    __tablename__ = 'compras'
    id = Column(String, primary_key=True)
    email_usuario = Column(String)
    id_produto = Column(String)
    data_compra = Column(Date)
    quantidade = Column(Float)
    preco_total = Column(Float)

# Conectar ao banco de dados SQLite
engine = create_engine('sqlite:///dbCoffee.db')
Base.metadata.create_all(engine)

# Criar uma sessão
Session = sessionmaker(bind=engine)
session = Session()