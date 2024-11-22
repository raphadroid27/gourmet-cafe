from uuid import uuid4
from flask import Flask, request, render_template, redirect, url_for, jsonify, session
import random 
import threading 
import time 
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from models import Usuario, Produto,Avaliacao, session as db_session

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
    return redirect(url_for('catalogo'))

@app.route('/finalizar_compra', methods=['GET', 'POST'])
def finalizar_compra():
    if request.method == 'POST':
        endereco = request.form.get('endereco')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        cep = request.form.get('cep')
        forma_pagamento = request.form.get('forma_pagamento')
        
        if forma_pagamento == 'cartao':
            numero_cartao = request.form.get('numero_cartao')
            nome_cartao = request.form.get('nome_cartao')
            validade_cartao = request.form.get('validade_cartao')
            cvv_cartao = request.form.get('cvv_cartao')
            # Adicione a lógica para processar o pagamento com cartão de crédito aqui
        
        elif forma_pagamento == 'pix':
            # Adicione a lógica para processar o pagamento com Pix aqui
        
            mensagem = "Compra finalizada com sucesso!"
        
        # Redireciona para a página de avaliação dos produtos
        return redirect(url_for('avaliar_produtos'))
    
    # Calcular o total dos itens no carrinho
    carrinho = session.get('carrinho', [])
    produtos = []
    total = 0
    for item in carrinho:
        produto = db_session.query(Produto).filter_by(id=item['produto_id']).first()
        if produto:
            subtotal = produto.preco * item['quantidade']
            produtos.append({
                'nome': produto.nome,
                'quantidade': item['quantidade'],
                'subtotal': subtotal
            })
            total += subtotal
    
    return render_template('finalizar_compra.html', produtos=produtos, total=total)

@app.route('/validar_cupom', methods=['POST'])
def validar_cupom():
    cupom = request.form.get('cupom')
    # Supondo que temos uma função que verifica a validade do cupom
    desconto = verificar_cupom(cupom)
    if desconto:
        return jsonify({'valido': True, 'desconto': desconto})
    else:
        return jsonify({'valido': False})

def verificar_cupom(cupom):
    # Exemplo de cupons válidos
    cupons_validos = {
        'DESCONTO10': 10,
        'DESCONTO20': 20
    }
    return cupons_validos.get(cupom.upper())

@app.route('/produto/<produto_id>', methods=['GET', 'POST'])
def ver_produto(produto_id):
    produto = db_session.query(Produto).filter_by(id=produto_id).first()
    avaliacoes = db_session.query(Avaliacao).filter_by(id_produto=produto_id).all()
    
    if request.method == 'POST':
        email_usuario = request.form.get('email_usuario')
        nota = int(request.form.get('nota'))
        comentario = request.form.get('comentario')
        
        nova_avaliacao = Avaliacao(
            email_usuario=email_usuario,
            id_produto=produto_id,
            nota=nota,
            comentario=comentario
        )
        db_session.add(nova_avaliacao)
        db_session.commit()
        return redirect(url_for('ver_produto', produto_id=produto_id))
    
    return render_template('produto.html', produto=produto, avaliacoes=avaliacoes)

@app.route('/editar_avaliacao/<avaliacao_id>', methods=['GET', 'POST'])
def editar_avaliacao(avaliacao_id):
    avaliacao = db_session.query(Avaliacao).filter_by(id=avaliacao_id).first()
    
    if request.method == 'POST':
        avaliacao.nota = int(request.form.get('nota'))
        avaliacao.comentario = request.form.get('comentario')
        db_session.commit()
        return redirect(url_for('ver_produto', produto_id=avaliacao.id_produto))
    
    return render_template('editar_avaliacao.html', avaliacao=avaliacao)

@app.route('/denunciar_avaliacao/<avaliacao_id>', methods=['POST'])
def denunciar_avaliacao(avaliacao_id):
    avaliacao = db_session.query(Avaliacao).filter_by(id=avaliacao_id).first()
    # Lógica para analisar a denúncia e tomar medidas apropriadas
    # Por exemplo, marcar a avaliação como denunciada ou removê-la
    db_session.delete(avaliacao)
    db_session.commit()
    return redirect(url_for('ver_produto', produto_id=avaliacao.id_produto))

@app.route('/avaliar_produtos', methods=['GET', 'POST'])
def avaliar_produtos():
    if request.method == 'POST':
        email_usuario = session.get('email')  # Supondo que o email do usuário está armazenado na sessão
        
        # Obter os produtos comprados pelo usuário
        carrinho = session.get('carrinho', [])
        produtos = []
        for item in carrinho:
            produto = db_session.query(Produto).filter_by(id=item['produto_id']).first()
            if produto:
                produtos.append(produto)
        
        # Processar as avaliações enviadas pelo formulário
        for produto in produtos:
            nota = request.form.get(f'nota_{produto.id}')
            comentario = request.form.get(f'comentario_{produto.id}')
            
            if nota:
                nova_avaliacao = Avaliacao(
                    email_usuario=email_usuario,
                    id_produto=produto.id,
                    nota=int(nota),
                    comentario=comentario
                )
                db_session.add(nova_avaliacao)
        
        db_session.commit()
        
        # Limpa o carrinho após a avaliação dos produtos
        session['carrinho'] = []
        
        mensagem = "Avaliações enviadas com sucesso!"
        return render_template('mensagem.html', mensagem=mensagem)
    
    # Obter os produtos comprados pelo usuário
    carrinho = session.get('carrinho', [])
    produtos = []
    for item in carrinho:
        produto = db_session.query(Produto).filter_by(id=item['produto_id']).first()
        if produto:
            produtos.append(produto)
    
    return render_template('avaliar_produtos.html', produtos=produtos)

@app.route('/devolucao', methods=['GET', 'POST'])
def devolucao():
    if request.method == 'POST':
        numero_pedido = request.form['numero_pedido']
        motivo = request.form['motivo']
        contato = request.form['contato']
        
        # Aqui você pode adicionar a lógica para registrar a devolução no banco de dados
        
        return render_template('devolucao_confirmacao.html', numero_pedido=numero_pedido)
    return render_template('devolucao.html')

@app.route('/status_devolucao', methods=['GET'])
def status_devolucao():
    numero_pedido = request.args.get('numero_pedido')
    
    # Aqui você pode adicionar a lógica para buscar o status da devolução no banco de dados
    
    status = "Em processamento"  # Exemplo de status
    return render_template('status_devolucao.html', numero_pedido=numero_pedido, status=status)

if __name__ == '__main__':
    threading.Thread(target=atualizar_codigos_recuperacao).start()
    app.run(debug=True)
