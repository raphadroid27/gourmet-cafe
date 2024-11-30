from sqlalchemy import create_engine, Column, String, Float, Date, Integer, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Configurar o banco de dados
Base = declarative_base()
engine = create_engine('sqlite:///dbCoffee.db')

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
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_usuario = Column(String, nullable=False)
    data_compra = Column(Date, nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_total = Column(Float, nullable=False)
    forma_pagamento = Column(String, nullable=False)
    numero_cartao = Column(String, nullable=True)
    nome_cartao = Column(String, nullable=True)
    validade_cartao = Column(String, nullable=True)
    cvv_cartao = Column(String, nullable=True)
    itens = relationship('ItensCompra', back_populates='compra')

class Avaliacao(Base):
    __tablename__ = 'avaliacoes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_usuario = Column(String)
    id_produto = Column(String, ForeignKey('produtos.id'))
    nota = Column(Integer)
    comentario = Column(String)
    produto = relationship('Produto')

class ItensCompra(Base):
    __tablename__ = 'itens_compra'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_compra = Column(Integer, ForeignKey('compras.id'), nullable=False)
    id_produto = Column(String, ForeignKey('produtos.id'), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)
    compra = relationship('Compra', back_populates='itens')
    produto = relationship('Produto')

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    sugestao = Column(String, nullable=False)
    respondido = Column(Boolean, default=False)

# Conectar ao banco de dados SQLite
engine = create_engine('sqlite:///dbCoffee.db')
Base.metadata.create_all(engine)

# Criar uma sessão
Session = sessionmaker(bind=engine)
session = Session()