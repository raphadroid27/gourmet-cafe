from uuid import uuid4
from flask import Flask, request, render_template, redirect, url_for, jsonify, session
import random 
import threading 
import time 
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from models import Usuario, Produto, session as db_session

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

def cadastrar_usuario(nome, email, senha):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "E-mail inválido!"
    if len(senha) < 8 or not re.search(r"[A-Za-z]", senha) or not re.search(r"[0-9]", senha) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        return "Senha não atende aos requisitos de segurança!"

    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    codigo_recuperacao = gerar_codigo_recuperacao()
    novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash)
    db_session.add(novo_usuario)
    db_session.commit()
    return f"Usuário {nome} cadastrado com sucesso."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalogo')
def catalogo():
    search = request.args.get('search', '')
    tipo = request.args.get('tipo', '')
    
    query = db_session.query(Produto).filter(Produto.nome.like(f'%{search}%'))
    
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
        db_session.add(novo_produto)
        db_session.commit()
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
    usuario = db_session.query(Usuario).filter_by(email=email).first()
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
        usuarios = db_session.query(Usuario).all()
        for usuario in usuarios:
            usuario.codigo_recuperacao = gerar_codigo_recuperacao()
        db_session.commit()

# Rota para página de recuperação de senha
@app.route('/recuperar_senha')
def recuperar_senha():
    return render_template('recuperar_senha.html')

# Rota para enviar código de recuperação
@app.route('/enviar_codigo', methods=['POST'])
def enviar_codigo():
    email = request.form['email']
    usuario = db_session.query(Usuario).filter_by(email=email).first()

    if usuario:
        usuario.codigo_recuperacao = gerar_codigo_recuperacao()
        db_session.commit()
        return "Código de recuperação enviado para o e-mail."
    mensagem="dsds"
    return render_template('mensagem.html', mensagem=mensagem)

# Rota para verificar código de recuperação
@app.route('/verificar_codigo', methods=['POST'])
def verificar_codigo():
    email = request.form['email']
    codigo_recuperacao = request.form['codigo_recuperacao']

    usuario = db_session.query(Usuario).filter_by(email=email, codigo_recuperacao=codigo_recuperacao).first()

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

    usuario = db_session.query(Usuario).filter_by(email=email, codigo_recuperacao=codigo_recuperacao).first()
    
    if usuario:
        usuario.senha = nova_senha
        usuario.codigo_recuperacao = None
        db_session.commit()
        return "Senha alterada com sucesso."
    return "Código de recuperação inválido."

# Rota para adicionar produto ao carrinho
@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    produto_id = request.form.get('produto_id')
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    carrinho = session['carrinho']
    
    # Verifica se o produto já está no carrinho
    for item in carrinho:
        if item['produto_id'] == produto_id:
            item['quantidade'] += 1
            break
    else:
        carrinho.append({'produto_id': produto_id, 'quantidade': 1})
    
    session['carrinho'] = carrinho
    return redirect(url_for('catalogo'))

# Rota para visualizar o carrinho
@app.route('/ver_carrinho')
def ver_carrinho():
    carrinho = session.get('carrinho', [])
    produtos = []
    total = 0
    
    for item in carrinho:
        produto = db_session.query(Produto).filter_by(id=item['produto_id']).first()
        if produto:
            produtos.append({
                'id': produto.id,
                'nome': produto.nome,
                'quantidade': item['quantidade'],
                'preco': produto.preco,
                'subtotal': produto.preco * item['quantidade'],
                'imagem': produto.imagem  # Adicione a URL da imagem aqui
            })
            total += produto.preco * item['quantidade']
    
    return render_template('carrinho.html', produtos=produtos, total=total)

@app.route('/remover_item', methods=['POST'])
def remover_item():
    produto_id = request.form.get('produto_id')
    carrinho = session.get('carrinho', [])
    
    carrinho = [item for item in carrinho if item['produto_id'] != produto_id]
    
    session['carrinho'] = carrinho
    return redirect(url_for('ver_carrinho'))

@app.route('/atualizar_quantidade', methods=['POST'])
def atualizar_quantidade():
    produto_id = request.form.get('produto_id')
    quantidade = int(request.form.get('quantidade'))
    carrinho = session.get('carrinho', [])
    
    for item in carrinho:
        if item['produto_id'] == produto_id:
            item['quantidade'] = quantidade
            break
    
    session['carrinho'] = carrinho
    return jsonify({'success': True})

@app.route('/limpar_carrinho')
def limpar_carrinho():
    session['carrinho'] = []
    return redirect(url_for('ver_carrinho'))

@app.route('/finalizar_compra', methods=['GET', 'POST'])
def finalizar_compra():
        if request.method == 'POST':
            # Aqui você pode adicionar a lógica para processar o pagamento e finalizar a compra
            session['carrinho'] = []  # Limpa o carrinho após a compra
            mensagem = "Compra finalizada com sucesso!"
            return render_template('mensagem.html', mensagem=mensagem)
        return render_template('finalizar_compra.html')    

if __name__ == '__main__':
    threading.Thread(target=atualizar_codigos_recuperacao).start()
    app.run(debug=True)
