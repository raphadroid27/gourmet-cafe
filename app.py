from uuid import uuid4
from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from email.mime.text import MIMEText
from models import Usuario, Produto, Avaliacao, Compra, ItensCompra, session as db_session
from functools import wraps
import hashlib
import re
import random
import threading
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def cadastrar_usuario(nome, email, senha):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "E-mail inválido!"
    if len(senha) < 8 or not re.search(r"[A-Za-z]", senha) or not re.search(r"[0-9]", senha) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        return "Senha não atende aos requisitos de segurança!"

    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    codigo_recuperacao = gerar_codigo_recuperacao()
    novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash, codigo_recuperacao=codigo_recuperacao)
    db_session.add(novo_usuario)
    db_session.commit()
    return f"Usuário {nome} cadastrado com sucesso."

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        usuario = db_session.query(Usuario).filter_by(email=email).first()
        if usuario and usuario.senha == senha_hash:
            session['user_id'] = usuario.email
            session['user_name'] = usuario.nome
            return redirect(url_for('catalogo'))
        else:
            mensagem = "Credenciais inválidas, tente novamente."
            return render_template('index.html', mensagem=mensagem)
    return render_template('index.html')

@app.route('/catalogo')
#@login_required
def catalogo():
    search = request.args.get('search', '')
    
    query = db_session.query(Produto).filter(Produto.nome.like(f'%{search}%'))
    
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

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('index'))

def gerar_codigo_recuperacao():
    return ''.join(random.choices('0123456789', k=6))

def enviar_email_confirmacao(email):
    mensagem = f"E-mail de confirmação enviado para {email}" 
    return render_template('mensagem.html', mensagem=mensagem)

def atualizar_codigos_recuperacao():
    while True:
        pass

        time.sleep(60)  # Espera por 1 minuto
        usuarios = db_session.query(Usuario).all()
        for usuario in usuarios:
            usuario.codigo_recuperacao = gerar_codigo_recuperacao()
        db_session.commit()

@app.route('/recuperar_senha')
def recuperar_senha():
    return render_template('recuperar_senha.html')

@app.route('/enviar_codigo', methods=['POST'])
def enviar_codigo():
    email = request.form['email']
    usuario = db_session.query(Usuario).filter_by(email=email).first()
    if usuario:
        usuario.codigo_recuperacao = gerar_codigo_recuperacao()
        db_session.commit()
        enviar_email_confirmacao(email)
        return "Código de recuperação enviado para o e-mail."
    return "E-mail não encontrado."

@app.route('/verificar_codigo', methods=['POST'])
def verificar_codigo():
    email = request.form['email']
    codigo_recuperacao = request.form['codigo_recuperacao']
    usuario = db_session.query(Usuario).filter_by(email=email, codigo_recuperacao=codigo_recuperacao).first()
    if usuario:
        return render_template('nova_senha.html', email=email, codigo_recuperacao=codigo_recuperacao)
    return "Código de recuperação inválido."

@app.route('/resetar_senha', methods=['POST'])
def resetar_senha():
    email = request.form['email']
    codigo_recuperacao = request.form['codigo_recuperacao']
    nova_senha = request.form['nova_senha']
    confirmar_senha = request.form['confirmar_senha']
    if nova_senha != confirmar_senha:
        return "As senhas não coincidem."
    usuario = db_session.query(Usuario).filter_by(email=email, codigo_recuperacao=codigo_recuperacao).first()
    if usuario:
        usuario.senha = hashlib.sha256(nova_senha.encode()).hexdigest()
        usuario.codigo_recuperacao = None
        db_session.commit()
        return "Senha redefinida com sucesso."
    return "Erro ao redefinir a senha."

@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    produto_id = request.form.get('produto_id')
    if not produto_id:
        return jsonify({'error': 'Produto ID não fornecido'}), 400

    produto = db_session.query(Produto).filter_by(id=produto_id).first()
    if not produto:
        return jsonify({'error': 'Produto não encontrado'}), 404

    if 'carrinho' not in session:
        session['carrinho'] = []

    # Verifica se o produto já está no carrinho
    for item in session['carrinho']:
        if item['id'] == produto.id:
            item['quantidade'] += 1
            break
    else:
        session['carrinho'].append({
            'id': produto.id,
            'nome': produto.nome,
            'preco': produto.preco,
            'quantidade': 1,
            'imagem': produto.imagem
        })

    session.modified = True
    return redirect(url_for('catalogo'))

@app.route('/ver_carrinho')
def ver_carrinho():
    carrinho = session.get('carrinho', [])
    total = sum(item['preco'] * item['quantidade'] for item in carrinho)
    for item in carrinho:
        item['subtotal'] = item['preco'] * item['quantidade']
    return render_template('carrinho.html', produtos=carrinho, total=total)

@app.route('/remover_item', methods=['POST'])
def remover_item():
    produto_id = request.form['produto_id']
    carrinho = session.get('carrinho', [])
    session['carrinho'] = [item for item in carrinho if item['id'] != produto_id]
    return redirect(url_for('ver_carrinho'))

@app.route('/atualizar_quantidade', methods=['POST'])
def atualizar_quantidade():
    produto_id = request.form['produto_id']
    quantidade = int(request.form['quantidade'])
    carrinho = session.get('carrinho', [])
    for item in carrinho:
        if item['id'] == produto_id:
            item['quantidade'] = quantidade
            break
    session['carrinho'] = carrinho
    return redirect(url_for('ver_carrinho'))

@app.route('/limpar_carrinho')
def limpar_carrinho():
    session.pop('carrinho', None)
    return redirect(url_for('ver_carrinho'))

@app.route('/finalizar_compra', methods=['GET', 'POST'])
@login_required
def finalizar_compra():
    if request.method == 'POST':
        endereco = request.form['endereco']
        cidade = request.form['cidade']
        estado = request.form['estado']
        cep = request.form['cep']
        carrinho = session.get('carrinho', [])
        total = sum(item['preco'] * item['quantidade'] for item in carrinho)
        
        # Obter o último código de pedido e gerar o próximo código sequencial
        ultimo_pedido = db_session.query(Compra).order_by(Compra.id.desc()).first()
        if ultimo_pedido:
            codigo_pedido = int(ultimo_pedido.id) + 1
        else:
            codigo_pedido = 1
        
        # Salvar a compra no banco de dados
        nova_compra = Compra(
            id=codigo_pedido,
            email_usuario=session['user_id'],
            data_compra=datetime.now().date(),
            quantidade=len(carrinho),
            preco_total=total
        )
        db_session.add(nova_compra)
        db_session.commit()
        
        # Salvar os itens comprados na tabela ItensCompra
        for item in carrinho:
            novo_item = ItensCompra(
                id_compra=codigo_pedido,
                id_produto=item['id'],
                quantidade=item['quantidade'],
                preco_unitario=item['preco']
            )
            db_session.add(novo_item)
        
        db_session.commit()
        
        # Limpar o carrinho
        session.pop('carrinho', None)
        
        # Redirecionar para o catálogo com uma mensagem de sucesso
        return redirect(url_for('catalogo', mensagem=f"Compra finalizada com sucesso! Código do pedido: {codigo_pedido}"))
    
    carrinho = session.get('carrinho', [])
    total = sum(item['preco'] * item['quantidade'] for item in carrinho)
    return render_template('finalizar_compra.html', produtos=carrinho, total=total)

@app.route('/validar_cupom', methods=['POST'])
def validar_cupom():
    cupom = request.form['cupom']
    desconto = verificar_cupom(cupom)
    if desconto:
        return jsonify({'desconto': desconto})
    return jsonify({'desconto': 0})

def verificar_cupom(cupom):
    cupons_validos = {
        'DESCONTO10': 10,
        'DESCONTO20': 20
    }
    return cupons_validos.get(cupom.upper())

@app.route('/produto/<produto_id>', methods=['GET', 'POST'])
def ver_produto(produto_id):
    produto = db_session.query(Produto).filter_by(id=produto_id).first()
    avaliacoes = db_session.query(Avaliacao).filter_by(id_produto=produto_id).all()
    return render_template('produto.html', produto=produto, avaliacoes=avaliacoes)

@app.route('/editar_avaliacao/<avaliacao_id>', methods=['GET', 'POST'])
def editar_avaliacao(avaliacao_id):
    avaliacao = db_session.query(Avaliacao).filter_by(id=avaliacao_id).first()
    if request.method == 'POST':
        avaliacao.nota = request.form['nota']
        avaliacao.comentario = request.form['comentario']
        db_session.commit()
        return redirect(url_for('ver_produto', produto_id=avaliacao.id_produto))
    return render_template('editar_avaliacao.html', avaliacao=avaliacao)

@app.route('/denunciar_avaliacao/<avaliacao_id>', methods=['POST'])
def denunciar_avaliacao(avaliacao_id):
    # Lógica para denunciar avaliação
    return "Avaliação denunciada."

@app.route('/avaliar_produtos', methods=['GET', 'POST'])
def avaliar_produtos():
    if request.method == 'POST':
        for produto_id in request.form:
            if produto_id.startswith('nota_'):
                id = produto_id.split('_')[1]
                nota = request.form[produto_id]
                comentario = request.form[f'comentario_{id}']
                nova_avaliacao = Avaliacao(
                    email_usuario=session['user_id'],
                    id_produto=id,
                    nota=nota,
                    comentario=comentario
                )
                db_session.add(nova_avaliacao)
                db_session.commit()
        return redirect(url_for('catalogo'))
    produtos = db_session.query(Produto).all()
    return render_template('avaliar_produtos.html', produtos=produtos)

@app.route('/avaliar_produto', methods=['POST'])
def avaliar_produto():
    produto_id = request.form['produto_id']
    nota = request.form['nota']
    comentario = request.form['comentario']
    nova_avaliacao = Avaliacao(
        email_usuario=session['user_id'],
        id_produto=produto_id,
        nota=nota,
        comentario=comentario
    )
    db_session.add(nova_avaliacao)
    db_session.commit()
    return redirect(url_for('ver_produto', produto_id=produto_id))

@app.route('/devolucao', methods=['GET', 'POST'])
def devolucao():
    if request.method == 'POST':
        numero_pedido = request.form['numero_pedido']
        motivo = request.form['motivo']
        contato = request.form['contato']
        # Lógica para processar a devolução
        return render_template('devolucao_confirmacao.html', numero_pedido=numero_pedido)
    return render_template('devolucao.html')

@app.route('/status_devolucao', methods=['GET'])
def status_devolucao():
    numero_pedido = request.args.get('numero_pedido')
    # Lógica para obter o status da devolução
    status = "Em processamento"  # Exemplo de status
    return render_template('status_devolucao.html', numero_pedido=numero_pedido, status=status)

@app.route('/area_cliente')
@login_required
def area_cliente():
    usuario = db_session.query(Usuario).filter_by(email=session['user_id']).first()
    pedidos = db_session.query(Compra).filter_by(email_usuario=session['user_id']).all()
    avaliacoes = db_session.query(Avaliacao).filter_by(email_usuario=session['user_id']).all()
    return render_template('area_cliente.html', usuario=usuario, pedidos=pedidos, avaliacoes=avaliacoes)

@app.route('/editar_usuario', methods=['GET', 'POST'])
@login_required
def editar_usuario():
    usuario = db_session.query(Usuario).filter_by(email=session['user_id']).first()
    if request.method == 'POST':
        usuario.nome = request.form['nome']
        usuario.data_nascimento = datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date()
        usuario.endereco_entrega = request.form['endereco_entrega']
        db_session.commit()
        return redirect(url_for('area_cliente'))
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/detalhes_pedido/<int:pedido_id>')
@login_required
def detalhes_pedido(pedido_id):
    pedido = db_session.query(Compra).filter_by(id=pedido_id).first()
    if not pedido:
        return "Pedido não encontrado", 404
    itens = db_session.query(ItensCompra).filter_by(id_compra=pedido_id).all()
    
    # Adicione prints para verificar os dados
    print(f"Pedido: {pedido}")
    print(f"Itens: {itens}")
    
    return render_template('detalhes_pedido.html', pedido=pedido, itens=itens)

if __name__ == '__main__':
    threading.Thread(target=atualizar_codigos_recuperacao).start()
    app.run(debug=True)
