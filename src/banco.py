import sqlite3
from pathlib import Path
from datetime import datetime

# ======================================================
# CONFIGURAÇÃO DO BANCO
# ======================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = BASE_DIR / "dados" / "banco.db"
CAMINHO_BANCO.parent.mkdir(exist_ok=True)

SALARIO_MINIMO = 1518.00          # valor 2025 — ajuste quando mudar
LIMITE_VULNERABILIDADE = 1.5      # múltiplos do salário mínimo per capita (critério PNAES)


def conectar():
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ======================================================
# CRIAÇÃO DAS TABELAS
# ======================================================

def criar_tabelas():
    with conectar() as conn:

        conn.executescript("""

        CREATE TABLE IF NOT EXISTS campus(
            id_campus INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            sigla TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS turmas(
            id_turma INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            curso TEXT NOT NULL,
            ano INTEGER NOT NULL,
            campus_id INTEGER NOT NULL,
            FOREIGN KEY(campus_id) REFERENCES campus(id_campus)
        );

        CREATE TABLE IF NOT EXISTS alunos(
            id_aluno INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            turma_id INTEGER NOT NULL,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY(turma_id) REFERENCES turmas(id_turma)
        );

        CREATE TABLE IF NOT EXISTS refeicoes(
            id_refeicao INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            data DATE NOT NULL,
            hora TIME NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'ALMOCO',
            FOREIGN KEY(aluno_id) REFERENCES alunos(id_aluno)
        );

        CREATE TABLE IF NOT EXISTS perfil_socioeconomico(
            id_perfil INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL UNIQUE,
            renda_familiar REAL DEFAULT 0,
            num_membros INTEGER DEFAULT 1,
            situacao_moradia TEXT DEFAULT 'NAO_INFORMADO',
            observacoes TEXT DEFAULT '',
            data_atualizacao DATE,
            FOREIGN KEY(aluno_id) REFERENCES alunos(id_aluno)
        );

        CREATE TABLE IF NOT EXISTS beneficios(
            id_beneficio INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL DEFAULT 0,
            data_inicio DATE NOT NULL,
            data_fim DATE,
            ativo INTEGER DEFAULT 1,
            observacoes TEXT DEFAULT '',
            FOREIGN KEY(aluno_id) REFERENCES alunos(id_aluno)
        );

        """)

        conn.execute("""
            INSERT OR IGNORE INTO campus (id_campus, nome, sigla)
            VALUES (1, 'IFAM Campus Humaitá', 'CHUM')
        """)

        conn.commit()


# ======================================================
# TURMAS
# ======================================================

def inserir_turma(nome, curso, ano, campus_id):
    with conectar() as conn:
        conn.execute(
            "INSERT INTO turmas(nome,curso,ano,campus_id) VALUES(?,?,?,?)",
            (nome, curso, ano, campus_id)
        )
        conn.commit()


def buscar_turma_nome(nome):
    with conectar() as conn:
        cursor = conn.execute("SELECT id_turma FROM turmas WHERE nome = ?", (nome,))
        resultado = cursor.fetchone()
        return resultado[0] if resultado else None


# ======================================================
# ALUNOS
# ======================================================

def inserir_aluno(nome, matricula, turma_id):
    with conectar() as conn:
        conn.execute(
            "INSERT INTO alunos(nome,matricula,turma_id) VALUES(?,?,?)",
            (nome, matricula, turma_id)
        )
        conn.commit()


def listar_alunos():
    with conectar() as conn:
        return conn.execute("""
            SELECT a.id_aluno, a.nome, a.matricula, t.nome
            FROM alunos a
            INNER JOIN turmas t ON a.turma_id = t.id_turma
            ORDER BY a.nome
        """).fetchall()


def buscar_aluno_matricula(matricula):
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM alunos WHERE matricula=?", (matricula,)
        ).fetchone()


def buscar_aluno_id(aluno_id):
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM alunos WHERE id_aluno=?", (aluno_id,)
        ).fetchone()


# ======================================================
# PERFIL SOCIOECONÔMICO
# ======================================================

SITUACOES_MORADIA = {
    'PROPRIA':       'Própria',
    'ALUGADA':       'Alugada',
    'CEDIDA':        'Cedida/Emprestada',
    'QUILOMBOLA':    'Quilombola / Indígena',
    'NAO_INFORMADO': 'Não informado',
}

TIPOS_BENEFICIO = {
    'TRANSPORTE': 'Auxílio transporte',
    'MORADIA':    'Auxílio moradia',
}


def calcular_renda_per_capita(renda_familiar, num_membros):
    if num_membros <= 0:
        return 0.0
    return renda_familiar / num_membros


def calcular_vulnerabilidade(renda_per_capita):
    return renda_per_capita <= (SALARIO_MINIMO * LIMITE_VULNERABILIDADE)


def salvar_perfil(aluno_id, renda_familiar, num_membros, situacao_moradia, observacoes=""):
    hoje = datetime.now().strftime("%Y-%m-%d")
    with conectar() as conn:
        conn.execute("""
            INSERT INTO perfil_socioeconomico
                (aluno_id, renda_familiar, num_membros, situacao_moradia, observacoes, data_atualizacao)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(aluno_id) DO UPDATE SET
                renda_familiar    = excluded.renda_familiar,
                num_membros       = excluded.num_membros,
                situacao_moradia  = excluded.situacao_moradia,
                observacoes       = excluded.observacoes,
                data_atualizacao  = excluded.data_atualizacao
        """, (aluno_id, renda_familiar, num_membros, situacao_moradia, observacoes, hoje))
        conn.commit()


def buscar_perfil_aluno(aluno_id):
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM perfil_socioeconomico WHERE aluno_id = ?", (aluno_id,)
        ).fetchone()


def listar_alunos_vulneraveis():
    limite = SALARIO_MINIMO * LIMITE_VULNERABILIDADE
    with conectar() as conn:
        return conn.execute("""
            SELECT
                a.nome, a.matricula, t.nome,
                p.renda_familiar, p.num_membros,
                ROUND(p.renda_familiar / p.num_membros, 2) AS renda_pc
            FROM perfil_socioeconomico p
            INNER JOIN alunos a ON p.aluno_id = a.id_aluno
            INNER JOIN turmas t ON a.turma_id  = t.id_turma
            WHERE (p.renda_familiar / p.num_membros) <= ?
            ORDER BY renda_pc ASC
        """, (limite,)).fetchall()


def listar_alunos_sem_perfil():
    with conectar() as conn:
        return conn.execute("""
            SELECT a.nome, a.matricula, t.nome
            FROM alunos a
            INNER JOIN turmas t ON a.turma_id = t.id_turma
            LEFT JOIN perfil_socioeconomico p ON p.aluno_id = a.id_aluno
            WHERE a.ativo = 1 AND p.id_perfil IS NULL
            ORDER BY a.nome
        """).fetchall()


def listar_vulneraveis_sem_beneficio():
    """Cruza vulnerabilidade com benefícios: alunos vulneráveis que hoje
    não recebem nenhum auxílio ativo — lista de prioridade para atendimento."""
    limite = SALARIO_MINIMO * LIMITE_VULNERABILIDADE
    with conectar() as conn:
        return conn.execute("""
            SELECT
                a.nome, a.matricula, t.nome,
                ROUND(p.renda_familiar / p.num_membros, 2) AS renda_pc
            FROM perfil_socioeconomico p
            INNER JOIN alunos a ON p.aluno_id = a.id_aluno
            INNER JOIN turmas t ON a.turma_id  = t.id_turma
            LEFT JOIN beneficios b ON b.aluno_id = a.id_aluno AND b.ativo = 1
            WHERE (p.renda_familiar / p.num_membros) <= ?
              AND b.id_beneficio IS NULL
            ORDER BY renda_pc ASC
        """, (limite,)).fetchall()


# ======================================================
# BENEFÍCIOS
# ======================================================

def inserir_beneficio(aluno_id, tipo, valor, data_inicio, data_fim=None, observacoes=""):
    with conectar() as conn:
        conn.execute("""
            INSERT INTO beneficios(aluno_id, tipo, valor, data_inicio, data_fim, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (aluno_id, tipo, valor, data_inicio, data_fim, observacoes))
        conn.commit()


def listar_beneficios():
    with conectar() as conn:
        return conn.execute("""
            SELECT b.id_beneficio, a.nome, a.matricula,
                   b.tipo, b.valor, b.data_inicio, b.data_fim, b.ativo,
                   b.aluno_id, b.observacoes
            FROM beneficios b
            INNER JOIN alunos a ON b.aluno_id = a.id_aluno
            ORDER BY b.ativo DESC, b.data_inicio DESC
        """).fetchall()


def editar_beneficio(id_beneficio, aluno_id, tipo, valor, data_inicio, data_fim=None, observacoes=""):
    with conectar() as conn:
        conn.execute("""
            UPDATE beneficios SET
                aluno_id   = ?,
                tipo       = ?,
                valor      = ?,
                data_inicio = ?,
                data_fim   = ?,
                observacoes = ?
            WHERE id_beneficio = ?
        """, (aluno_id, tipo, valor, data_inicio, data_fim or None, observacoes, id_beneficio))
        conn.commit()


def listar_beneficios_aluno(aluno_id):
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM beneficios WHERE aluno_id = ? ORDER BY data_inicio DESC",
            (aluno_id,)
        ).fetchall()


def encerrar_beneficio(id_beneficio):
    hoje = datetime.now().strftime("%Y-%m-%d")
    with conectar() as conn:
        conn.execute("""
            UPDATE beneficios SET ativo = 0, data_fim = ?
            WHERE id_beneficio = ?
        """, (hoje, id_beneficio))
        conn.commit()


# ======================================================
# DADOS PARA O PAINEL
# ======================================================

def stats_beneficios_ativos():
    with conectar() as conn:
        return conn.execute("""
            SELECT tipo, COUNT(*), SUM(valor)
            FROM beneficios
            WHERE ativo = 1
            GROUP BY tipo
        """).fetchall()


def stats_total_alunos():
    with conectar() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM alunos WHERE ativo = 1"
        ).fetchone()[0]


def stats_total_refeicoes_hoje():
    hoje = datetime.now().strftime("%Y-%m-%d")
    with conectar() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM refeicoes WHERE data = ?", (hoje,)
        ).fetchone()[0]


def stats_alunos_com_perfil():
    with conectar() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM perfil_socioeconomico"
        ).fetchone()[0]


def stats_alunos_vulneraveis():
    limite = SALARIO_MINIMO * LIMITE_VULNERABILIDADE
    with conectar() as conn:
        return conn.execute("""
            SELECT COUNT(*) FROM perfil_socioeconomico
            WHERE (renda_familiar / num_membros) <= ?
        """, (limite,)).fetchone()[0]


def stats_alunos_por_turma():
    with conectar() as conn:
        return conn.execute("""
            SELECT t.nome, COUNT(*) AS total
            FROM alunos a
            INNER JOIN turmas t ON a.turma_id = t.id_turma
            WHERE a.ativo = 1
            GROUP BY t.nome
            ORDER BY total DESC
        """).fetchall()


def stats_situacao_moradia():
    with conectar() as conn:
        return conn.execute("""
            SELECT situacao_moradia, COUNT(*) AS total
            FROM perfil_socioeconomico
            GROUP BY situacao_moradia
            ORDER BY total DESC
        """).fetchall()


def stats_vulnerabilidade_x_beneficio():
    """Cruza vulnerabilidade socioeconômica com cobertura de benefícios ativos.
    Retorna (qtd_com_beneficio, qtd_sem_beneficio) entre os alunos vulneráveis."""
    limite = SALARIO_MINIMO * LIMITE_VULNERABILIDADE
    with conectar() as conn:
        total_vulneraveis = conn.execute("""
            SELECT COUNT(*) FROM perfil_socioeconomico
            WHERE (renda_familiar / num_membros) <= ?
        """, (limite,)).fetchone()[0]

        com_beneficio = conn.execute("""
            SELECT COUNT(DISTINCT p.aluno_id)
            FROM perfil_socioeconomico p
            INNER JOIN beneficios b ON b.aluno_id = p.aluno_id AND b.ativo = 1
            WHERE (p.renda_familiar / p.num_membros) <= ?
        """, (limite,)).fetchone()[0]

        return com_beneficio, total_vulneraveis - com_beneficio


# ======================================================
# INICIALIZAÇÃO
# ======================================================

if __name__ == "__main__":
    criar_tabelas()
    print("=" * 50)
    print("BANCO DE DADOS CRIADO COM SUCESSO!")
    print(f"Arquivo: {CAMINHO_BANCO}")
    print("=" * 50)