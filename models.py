from sqlalchemy import create_engine, Column, String, Float, Date, Integer, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from sqlalchemy import DateTime

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
    enderecos = relationship('Endereco', back_populates='usuario')
    cartoes_credito = relationship('CartaoCredito', back_populates='usuario')
    compras = relationship('Compra', back_populates='usuario')

class Endereco(Base):
    __tablename__ = 'enderecos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_usuario = Column(String, ForeignKey('usuarios.email'), nullable=False)
    endereco = Column(String, nullable=False)
    cidade = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    cep = Column(String, nullable=False)
    usuario = relationship('Usuario', back_populates='enderecos')
    compras = relationship('Compra', back_populates='endereco')

class CartaoCredito(Base):
    __tablename__ = 'cartoes_credito'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_usuario = Column(String, ForeignKey('usuarios.email'), nullable=False)
    numero_cartao = Column(String, nullable=False)
    nome_cartao = Column(String, nullable=False)
    validade_cartao = Column(String, nullable=False)
    cvv_cartao = Column(String, nullable=False)
    usuario = relationship('Usuario', back_populates='cartoes_credito')

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
    email_usuario = Column(String, ForeignKey('usuarios.email'), nullable=False)
    data_compra = Column(Date, nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_total = Column(Float, nullable=False)
    forma_pagamento = Column(String, nullable=False)
    numero_cartao = Column(String)
    nome_cartao = Column(String)
    validade_cartao = Column(String)
    cvv_cartao = Column(String)
    endereco_entrega = Column(Integer, ForeignKey('enderecos.id'), nullable=False)
    usuario = relationship('Usuario', back_populates='compras')
    itens = relationship('ItensCompra', back_populates='compra')
    endereco = relationship('Endereco', back_populates='compras')

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
    __tablename__ = 'feedbacks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    sugestao = Column(String, nullable=False)
    respondido = Column(Boolean, default=False)
    resposta = Column(String, nullable=True)
    data = Column(DateTime, default=datetime.utcnow, nullable=False)

class Devolucao(Base):
    __tablename__ = 'devolucoes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_pedido = Column(String, nullable=False)
    motivo = Column(String, nullable=False)
    contato = Column(String, nullable=False)
    respondido = Column(Boolean, default=False)
    resposta = Column(String, nullable=True)

# Conectar ao banco de dados SQLite
engine = create_engine('sqlite:///dbCoffee.db')
Base.metadata.create_all(engine)

# Criar uma sessão
Session = sessionmaker(bind=engine)
session = Session()