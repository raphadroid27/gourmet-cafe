from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime
from sqlalchemy.sql import text
from datetime import datetime

engine = create_engine('sqlite:///dbCoffee.db')
metadata = MetaData()

# Refletir as tabelas existentes no banco de dados
metadata.reflect(bind=engine)

devolucoes = Table('devolucoes', metadata, autoload_with=engine)

# Verificar se as colunas 'email_usuario' e 'data_solicitacao' já existem
with engine.connect() as conn:
    if 'email_usuario' not in devolucoes.c:
        conn.execute(text('ALTER TABLE devolucoes ADD COLUMN email_usuario STRING'))
        print("Coluna 'email_usuario' adicionada à tabela 'devolucoes'.")

    if 'data_solicitacao' not in devolucoes.c:
        conn.execute(text('ALTER TABLE devolucoes ADD COLUMN data_solicitacao DATETIME'))
        conn.execute(text('UPDATE devolucoes SET data_solicitacao = :data WHERE data_solicitacao IS NULL'), {'data': datetime.utcnow()})
        print("Coluna 'data_solicitacao' adicionada à tabela 'devolucoes' e linhas existentes atualizadas.")
    else:
        print("A coluna 'data_solicitacao' já existe na tabela 'devolucoes'.")