from sqlalchemy import create_engine, MetaData, Table, Column, DateTime
from sqlalchemy.sql import text
from datetime import datetime

engine = create_engine('sqlite:///dbCoffee.db')
metadata = MetaData()

# Refletir as tabelas existentes no banco de dados
metadata.reflect(bind=engine)

feedbacks = Table('feedbacks', metadata, autoload_with=engine)

# Adicionar a coluna 'data' sem valor padrão
with engine.connect() as conn:
    conn.execute(text('ALTER TABLE feedbacks ADD COLUMN data DATETIME'))

    # Atualizar as linhas existentes para definir a data atual
    conn.execute(text('UPDATE feedbacks SET data = CURRENT_TIMESTAMP WHERE data IS NULL'))

print("Coluna 'data' adicionada à tabela 'feedbacks' e linhas existentes atualizadas.")