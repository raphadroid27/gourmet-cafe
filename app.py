from uuid import uuid4
from flask import Flask, request, render_template, redirect, url_for, jsonify
import random 
import threading 
import time 
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from models import Usuario, Produto, session

app = Flask(__name__)

def cadastrar_usuario(nome, email, senha):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "E-mail inválido!"
    if len(senha) < 8 or not re.search(r"[A-Za-z]", senha) or not re.search(r"[0-9]", senha) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        return "Senha não atende aos requisitos de segurança!"

    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    codigo_recuperacao = gerar_codigo_recuperacao()
    novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash)
    session.add(novo_usuario)
    session.commit()
    return f"Usuário {nome} cadastrado com sucesso."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalogo')
def catalogo():
    search = request.args.get('search', '')
    tipo = request.args.get('tipo', '')
    
    query = session.query(Produto).filter(Produto.nome.like(f'%{search}%'))
    
    if tipo:
        query = query.filter(Produto.tipo == tipo)
    
    # Ordenar os resultados por nome
    produtos = query.order_by(Produto.nome).all()
    
    return render_template('catalogo.html', produtos=produtos)

@app.route('/cadastrar_produto', methods=['GET', 'POST'])
def cadastrar_produto():
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = request.form['preco']
        imagem = request.form['imagem']
        tipo = request.form['tipo']
        ingredientes = request.form['ingredientes']

        novo_produto = Produto(
            id=str(uuid4()), 
            nome=nome, 
            descricao=descricao, 
            preco=float(preco), 
            imagem=imagem, 
            tipo=tipo, 
            ingredientes=ingredientes
        )
        session.add(novo_produto)
        session.commit()
        mensagem = "Produto cadastrado com sucesso!"
        return render_template('mensagem.html', mensagem=mensagem)
    return render_template('cadastrar_produto.html')
        

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    mensagem = cadastrar_usuario(nome, email, senha)
    return render_template('mensagem.html', mensagem=mensagem)

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    senha = request.form['senha']
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    usuario = session.query(Usuario).filter_by(email=email).first()
    if usuario and usuario.senha == senha_hash:
        return redirect(url_for('catalogo'))
    else:
        mensagem = "E-mail ou senha incorretos!" 
        return render_template('mensagem.html', mensagem=mensagem)
    
# Função para gerar código de recuperação
def gerar_codigo_recuperacao():
    return ''.join(random.choices('0123456789', k=6))

# Função para enviar e-mail de confirmação (Exemplo simplificado)
def enviar_email_confirmacao(email):
    mensagem = f"E-mail de confirmação enviado para {email}" 
    return render_template('mensagem.html', mensagem=mensagem)

# Função para atualizar códigos de recuperação a cada hora
def atualizar_codigos_recuperacao():
    while True:
        time.sleep(60)  # Espera por 1 minuto
        usuarios = session.query(Usuario).all()
        for usuario in usuarios:
            usuario.codigo_recuperacao = gerar_codigo_recuperacao()
        session.commit()

# Rota para página de recuperação de senha
@app.route('/recuperar_senha')
def recuperar_senha():
    return render_template('recuperar_senha.html')

# Rota para enviar código de recuperação
@app.route('/enviar_codigo', methods=['POST'])
def enviar_codigo():
    email = request.form['email']
    usuario = session.query(Usuario).filter_by(email=email).first()

    if usuario:
        usuario.codigo_recuperacao = gerar_codigo_recuperacao()
        session.commit()
        return "Código de recuperação enviado para o e-mail."
    mensagem="dsds"
    return render_template('mensagem.html', mensagem=mensagem)

# Rota para verificar código de recuperação
@app.route('/verificar_codigo', methods=['POST'])
def verificar_codigo():
    email = request.form['email']
    codigo_recuperacao = request.form['codigo_recuperacao']

    usuario = session.query(Usuario).filter_by(email=email, codigo_recuperacao=codigo_recuperacao).first()

    if usuario:
        return render_template('nova_senha.html', email=email, codigo_recuperacao=codigo_recuperacao)
    return "Código de recuperação inválido."

# Rota para resetar senha
@app.route('/resetar_senha', methods=['POST'])
def resetar_senha():
    email = request.form['email']
    codigo_recuperacao = request.form['codigo_recuperacao']
    nova_senha = request.form['nova_senha']
    confirmar_senha = request.form['confirmar_senha']

    if nova_senha != confirmar_senha:
        return "As senhas não coincidem."

    regex = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    if not re.match(regex, nova_senha):
        return "A senha deve conter pelo menos 8 caracteres, incluindo uma letra, um número e um caractere especial."

    usuario = session.query(Usuario).filter_by(email=email, codigo_recuperacao=codigo_recuperacao).first()
    
    if usuario:
        usuario.senha = nova_senha
        usuario.codigo_recuperacao = None
        session.commit()
        return "Senha alterada com sucesso."
    return "Código de recuperação inválido."

# Rota para adicionar produto ao carrinho
@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    produto_id = request.form['produto_id']
    quantidade = int(request.form['quantidade'])
    
    produto = session.query(Produto).filter_by(id=produto_id).first()
    
    if not produto:
        return "Produto não encontrado."
    
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    carrinho = session['carrinho']
    carrinho.append({'produto_id': produto_id, 'quantidade': quantidade, 'preco': produto.preco})
    session['carrinho'] = carrinho
    
    return redirect(url_for('ver_carrinho'))

# Rota para visualizar o carrinho
@app.route('/ver_carrinho')
def ver_carrinho():
    if 'carrinho' not in session:
        return render_template('carrinho.html', produtos=[], total=0)
    
    carrinho = session['carrinho']
    produtos = []
    total = 0
    
    for item in carrinho:
        produto = session.query(Produto).filter_by(id=item['produto_id']).first()
        if produto:
            produtos.append({
                'nome': produto.nome,
                'quantidade': item['quantidade'],
                'preco': produto.preco,
                'subtotal': produto.preco * item['quantidade']
            })
            total += produto.preco * item['quantidade']
    
    return render_template('carrinho.html', produtos=produtos, total=total)

if __name__ == '__main__':
    threading.Thread(target=atualizar_codigos_recuperacao).start()
    app.run(debug=True)
