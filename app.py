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
            app.logger.warning('Acesso não autorizado. Redirecionando para a página inicial.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def cadastrar_usuario(nome, email, senha):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "E-mail inválido!"
    if len(senha) < 8 or not re.search(r"[A-Za-z]", senha) or not re.search(r"[0-9]", senha) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        return "Senha não atende aos requisitos de segurança!"

    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        codigo_recuperacao = gerar_codigo_recuperacao()
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash, codigo_recuperacao=codigo_recuperacao)
        db_session.add(novo_usuario)
        db_session.commit()
        return f"Usuário {nome} cadastrado com sucesso."
    except Exception as e:
        db_session.rollback()
        return str(e)

@app.route('/')
def index():
    try:
        produtos = db_session.query(Produto).all()
        return render_template('index.html', produtos=produtos)
    except Exception as e:
        app.logger.error(f"Erro ao carregar a página inicial: {str(e)}")
        return str(e), 500

@app.route('/catalogo')
def catalogo():
    try:
        produtos = db_session.query(Produto).all()
        return render_template('catalogo.html', produtos=produtos)
    except Exception as e:
        app.logger.error(f"Erro ao carregar catálogo: {str(e)}")
        return str(e), 500

@app.route('/cadastrar_produto', methods=['GET', 'POST'])
def cadastrar_produto():
    if request.method == 'POST':
        try:
            nome = request.form['nome']
            descricao = request.form['descricao']
            preco = float(request.form['preco'])
            novo_produto = Produto(nome=nome, descricao=descricao, preco=preco)
            db_session.add(novo_produto)
            db_session.commit()
            return redirect(url_for('catalogo'))
        except Exception as e:
            db_session.rollback()
            app.logger.error(f"Erro ao cadastrar produto: {str(e)}")
            return str(e), 500

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
    try:
        session.pop('user_id', None)
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Erro ao fazer logout: {str(e)}")
        return str(e), 500

def enviar_email_confirmacao(email):
    mensagem = f"E-mail de confirmação enviado para {email}" 
    return render_template('mensagem.html', mensagem=mensagem)

def gerar_codigo_recuperacao():
    return ''.join(random.choices('0123456789', k=6))

def atualizar_codigos_recuperacao():
    while True:
        time.sleep(60)  # Espera por 1 minuto
        usuarios = db_session.query(Usuario).all()
        for usuario in usuarios:
            usuario.codigo_recuperacao = gerar_codigo_recuperacao()
        db_session.commit()

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form['email']
        try:
            usuario = db_session.query(Usuario).filter_by(email=email).first()
            if usuario:
                codigo_recuperacao = gerar_codigo_recuperacao()
                usuario.codigo_recuperacao = codigo_recuperacao
                db_session.commit()
                # Enviar e-mail com o código de recuperação
                return "Código de recuperação enviado para o e-mail."
            else:
                return "E-mail não encontrado", 404
        except Exception as e:
            db_session.rollback()
            app.logger.error(f"Erro ao recuperar senha: {str(e)}")
            return str(e), 500

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

@app.route('/resetar_senha/<codigo_recuperacao>', methods=['GET', 'POST'])
def resetar_senha(codigo_recuperacao):
    if request.method == 'POST':
        nova_senha = request.form['nova_senha']
        confirmar_senha = request.form['confirmar_senha']

        if nova_senha != confirmar_senha:
            return "As senhas não coincidem", 400

        if len(nova_senha) < 8 or not re.search(r"[A-Za-z]", nova_senha) or not re.search(r"[0-9]", nova_senha) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", nova_senha):
            return "Senha não atende aos requisitos de segurança!"

        try:
            usuario = db_session.query(Usuario).filter_by(codigo_recuperacao=codigo_recuperacao).first()
            if usuario:
                usuario.senha = hashlib.sha256(nova_senha.encode()).hexdigest()
                usuario.codigo_recuperacao = None
                db_session.commit()
                return redirect(url_for('login'))
            else:
                return "Código de recuperação inválido", 404
        except Exception as e:
            db_session.rollback()
            app.logger.error(f"Erro ao resetar senha: {str(e)}")
            return str(e), 500

    return render_template('resetar_senha.html', codigo_recuperacao=codigo_recuperacao)

@app.route('/adicionar_ao_carrinho/<produto_id>')
def adicionar_ao_carrinho(produto_id):
    try:
        produto = db_session.query(Produto).filter_by(id=produto_id).first()
        if not produto:
            return "Produto não encontrado", 404

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
    except Exception as e:
        app.logger.error(f"Erro ao adicionar produto ao carrinho: {str(e)}")
        return str(e), 500

@app.route('/ver_carrinho')
def ver_carrinho():
    try:
        carrinho = session.get('carrinho', [])
        total = sum(item['preco'] * item['quantidade'] for item in carrinho)
        for item in carrinho:
            item['subtotal'] = item['preco'] * item['quantidade']
        return render_template('ver_carrinho.html', carrinho=carrinho, total=total)
    except Exception as e:
        app.logger.error(f"Erro ao visualizar o carrinho: {str(e)}")
        return str(e), 500

@app.route('/remover_item', methods=['POST'])
def remover_item():
    produto_id = request.form['produto_id']
    carrinho = session.get('carrinho', [])
    session['carrinho'] = [item for item in carrinho if item['id'] != produto_id]
    return redirect(url_for('ver_carrinho'))

@app.route('/remover_do_carrinho/<produto_id>')
def remover_do_carrinho(produto_id):
    try:
        if 'carrinho' in session:
            for item in session['carrinho']:
                if item['id'] == int(produto_id):
                    session['carrinho'].remove(item)
                    session.modified = True
                    break
        return redirect(url_for('ver_carrinho'))
    except Exception as e:
        app.logger.error(f"Erro ao remover produto do carrinho: {str(e)}")
        return str(e), 500

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

@app.route('/atualizar_carrinho', methods=['POST'])
def atualizar_carrinho():
    try:
        for item in session['carrinho']:
            item_id = str(item['id'])
            if item_id in request.form:
                item['quantidade'] = int(request.form[item_id])
        session.modified = True
        return redirect(url_for('ver_carrinho'))
    except Exception as e:
        app.logger.error(f"Erro ao atualizar o carrinho: {str(e)}")
        return str(e), 500

@app.route('/limpar_carrinho')
def limpar_carrinho():
    session.pop('carrinho', None)
    return redirect(url_for('ver_carrinho'))

@app.route('/finalizar_compra', methods=['GET', 'POST'])
@login_required
def finalizar_compra():
    if request.method == 'POST':
        try:
            endereco = request.form['endereco']
            cidade = request.form['cidade']
            estado = request.form['estado']
            cep = request.form['cep']
            carrinho = session.get('carrinho', [])
            total = sum(item['preco'] * item['quantidade'] for item in carrinho)

            ultimo_pedido = db_session.query(Compra).order_by(Compra.id.desc()).first()
            codigo_pedido = int(ultimo_pedido.id) + 1 if ultimo_pedido else 1

            nova_compra = Compra(
                id=codigo_pedido,
                email_usuario=session['user_id'],
                data_compra=datetime.now().date(),
                quantidade=len(carrinho),
                preco_total=total
            )
            db_session.add(nova_compra)

            for item in carrinho:
                novo_item = ItensCompra(
                    id_compra=codigo_pedido,
                    id_produto=item['id'],
                    quantidade=item['quantidade'],
                    preco_unitario=item['preco']
                )
                db_session.add(novo_item)

            db_session.commit()
            session.pop('carrinho', None)
            return redirect(url_for('catalogo', mensagem=f"Compra finalizada com sucesso! Código do pedido: {codigo_pedido}"))
        except Exception as e:
            db_session.rollback()
            return str(e), 500

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

@app.route('/aplicar_cupom', methods=['POST'])
def aplicar_cupom():
    try:
        cupom = request.form['cupom']
        desconto = verificar_cupom(cupom)
        return jsonify({'desconto': desconto})
    except Exception as e:
        app.logger.error(f"Erro ao aplicar cupom: {str(e)}")
        return jsonify({'desconto': 0}), 500

def verificar_cupom(cupom):
    try:
        cupons_validos = {
            'DESCONTO10': 10,
            'DESCONTO20': 20
        }
        return cupons_validos.get(cupom.upper(), 0)
    except Exception as e:
        app.logger.error(f"Erro ao verificar cupom: {str(e)}")
        return 0

@app.route('/produto/<produto_id>', methods=['GET', 'POST'])
def ver_produto(produto_id):
    try:
        produto = db_session.query(Produto).filter_by(id=produto_id).first()
        if not produto:
            return "Produto não encontrado", 404
        return render_template('ver_produto.html', produto=produto)
    except Exception as e:
        app.logger.error(f"Erro ao carregar produto: {str(e)}")
        return str(e), 500

@app.route('/editar_avaliacao/<avaliacao_id>', methods=['GET', 'POST'])
def editar_avaliacao(avaliacao_id):
    avaliacao = db_session.query(Avaliacao).filter_by(id=avaliacao_id).first()
    if not avaliacao:
        return "Avaliação não encontrada", 404

    if request.method == 'POST':
        try:
            avaliacao.nota = request.form['nota']
            avaliacao.comentario = request.form['comentario']
            db_session.commit()
            return redirect(url_for('ver_produto', produto_id=avaliacao.id_produto))
        except Exception as e:
            db_session.rollback()
            return str(e), 500

    return render_template('editar_avaliacao.html', avaliacao=avaliacao)

@app.route('/avaliar_produtos', methods=['GET', 'POST'])
def avaliar_produtos():
    if request.method == 'POST':
        try:
            for produto_id in request.form:
                if (produto_id.startswith('nota_')):
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
        except Exception as e:
            db_session.rollback()
            return str(e), 500

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
    if not usuario:
        return "Usuário não encontrado", 404

    if request.method == 'POST':
        try:
            usuario.nome = request.form['nome']
            usuario.data_nascimento = datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date()
            usuario.endereco_entrega = request.form['endereco_entrega']
            db_session.commit()
            return redirect(url_for('area_cliente'))
        except Exception as e:
            db_session.rollback()
            return str(e), 500

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        try:
            usuario = db_session.query(Usuario).filter_by(email=email, senha=senha_hash).first()
            if usuario:
                session['user_id'] = usuario.email
                return redirect(url_for('index'))
            else:
                return "E-mail ou senha incorretos", 401
        except Exception as e:
            app.logger.error(f"Erro ao fazer login: {str(e)}")
            return str(e), 500

    return render_template('login.html')

if __name__ == '__main__':
    threading.Thread(target=atualizar_codigos_recuperacao).start()
    app.run(debug=True)