import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash
import datetime

app = Flask(__name__)

# Configuração para OpenShift - usa variáveis de ambiente
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fiat-demo-secret-key-openshift')

# Configuração do banco de dados
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'rhel610-postgres'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'fiat_legacy'),
    'user': os.getenv('DB_USER', 'fiat_user'),
    'password': os.getenv('DB_PASSWORD', 'fiat123')
}

def get_db_connection():
    """Estabelece conexão com o PostgreSQL 8.4 na VM RHEL6"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            connect_timeout=10
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        app.logger.error(f"Erro ao conectar ao banco: {e}")
        return None

@app.route('/')
def index():
    """Página inicial - Lista todos os veículos"""
    conn = get_db_connection()
    if conn is None:
        flash('Erro: Não foi possível conectar ao banco de dados', 'error')
        return render_template('index.html', veiculos=[])
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM veiculos ORDER BY id;')
        veiculos = cur.fetchall()
        cur.close()
        
        # Formatar dados para exibição
        veiculos_formatados = []
        for veiculo in veiculos:
            veiculo_list = list(veiculo)
            if isinstance(veiculo_list[5], datetime.date):
                veiculo_list[5] = veiculo_list[5].strftime('%Y-%m-%d')
            veiculos_formatados.append(veiculo_list)
            
        return render_template('index.html', veiculos=veiculos_formatados)
    except Exception as e:
        app.logger.error(f"Erro ao buscar veículos: {e}")
        flash(f'Erro ao buscar veículos: {e}', 'error')
        return render_template('index.html', veiculos=[])
    finally:
        conn.close()

@app.route('/veiculo/novo', methods=['GET', 'POST'])
def novo_veiculo():
    """Adiciona novo veículo"""
    if request.method == 'POST':
        modelo = request.form['modelo']
        ano = request.form['ano']
        cor = request.form['cor']
        preco = request.form['preco']
        data_fabricacao = request.form['data_fabricacao']
        disponivel = 'disponivel' in request.form
        
        conn = get_db_connection()
        if conn is None:
            flash('Erro: Não foi possível conectar ao banco de dados', 'error')
            return redirect(url_for('index'))
        
        try:
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO veiculos (modelo, ano, cor, preco, data_fabricacao, disponivel) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (modelo, int(ano), cor, float(preco), data_fabricacao, bool(disponivel))
            )
            conn.commit()
            cur.close()
            flash('Veículo adicionado com sucesso!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            conn.rollback()
            app.logger.error(f"Erro ao adicionar veículo: {e}")
            flash(f'Erro ao adicionar veículo: {e}', 'error')
            return render_template('novo_veiculo.html')
        finally:
            conn.close()
    
    return render_template('novo_veiculo.html')

@app.route('/veiculo/editar/<int:id>', methods=['GET', 'POST'])
def editar_veiculo(id):
    """Edita veículo existente"""
    conn = get_db_connection()
    if conn is None:
        flash('Erro: Não foi possível conectar ao banco de dados', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        modelo = request.form['modelo']
        ano = request.form['ano']
        cor = request.form['cor']
        preco = request.form['preco']
        data_fabricacao = request.form['data_fabricacao']
        disponivel = 'disponivel' in request.form
        
        try:
            cur = conn.cursor()
            cur.execute(
                'UPDATE veiculos SET modelo=%s, ano=%s, cor=%s, preco=%s, data_fabricacao=%s, disponivel=%s '
                'WHERE id=%s',
                (modelo, int(ano), cor, float(preco), data_fabricacao, bool(disponivel), id)
            )
            conn.commit()
            cur.close()
            flash('Veículo atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            conn.rollback()
            app.logger.error(f"Erro ao atualizar veículo: {e}")
            flash(f'Erro ao atualizar veículo: {e}', 'error')
        finally:
            conn.close()
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM veiculos WHERE id = %s', (id,))
        veiculo = cur.fetchone()
        cur.close()
        
        if veiculo is None:
            flash('Veículo não encontrado', 'error')
            return redirect(url_for('index'))
        
        # Formatar veículo para template
        veiculo_formatado = list(veiculo)
        if isinstance(veiculo_formatado[5], datetime.date):
            veiculo_formatado[5] = veiculo_formatado[5].strftime('%Y-%m-%d')
            
        return render_template('editar_veiculo.html', veiculo=veiculo_formatado)
    except Exception as e:
        app.logger.error(f"Erro ao buscar veículo: {e}")
        flash(f'Erro ao buscar veículo: {e}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/veiculo/deletar/<int:id>')
def deletar_veiculo(id):
    """Deleta veículo"""
    conn = get_db_connection()
    if conn is None:
        flash('Erro: Não foi possível conectar ao banco de dados', 'error')
        return redirect(url_for('index'))
    
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM veiculos WHERE id = %s', (id,))
        conn.commit()
        cur.close()
        flash('Veículo deletado com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Erro ao deletar veículo: {e}")
        flash(f'Erro ao deletar veículo: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/health')
def health():
    """Endpoint de health check para OpenShift"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('SELECT 1')
            cur.close()
            conn.close()
            return "OK", 200
    except Exception as e:
        app.logger.error(f"Health check failed: {e}")
    return "Database connection failed", 500

@app.route('/info')
def info():
    """Página de informações do sistema"""
    db_status = "OK"
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
        else:
            db_status = "ERROR"
    except:
        db_status = "ERROR"
    
    return f"""
    <h1>FIAT - Sistema Legado Modernizado</h1>
    <p><strong>Status do Banco:</strong> {db_status}</p>
    <p><strong>Host do Banco:</strong> {DB_CONFIG['host']}:{DB_CONFIG['port']}</p>
    <p><strong>Database:</strong> {DB_CONFIG['database']}</p>
    <p><strong>Usuário:</strong> {DB_CONFIG['user']}</p>
    <p><strong>OpenShift Project:</strong> {os.getenv('OPENSHIFT_BUILD_NAMESPACE', 'N/A')}</p>
    <a href="/">Voltar para a aplicação</a>
    """

if __name__ == '__main__':
    # Configuração para OpenShift
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    
    # Use Gunicorn se disponível, senão use Flask dev server
    if os.getenv('OPENSHIFT_BUILD_NAME'):
        # Em produção no OpenShift
        app.run(host=host, port=port, debug=False)
    else:
        # Em desenvolvimento
        app.run(host=host, port=port, debug=True)