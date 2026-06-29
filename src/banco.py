import sqlite3
from pathlib import Path
from datetime import datetime

# ======================================================
# CONFIGURAÇÃO DO BANCO
# ======================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = BASE_DIR / "dados" / "banco_ticket.db"
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
# CAMPUS
# ======================================================

def inserir_campus(nome, sigla):
    with conectar() as conn:
        conn.execute("INSERT INTO campus(nome,sigla) VALUES(?,?)", (nome, sigla))
        conn.commit()


def listar_campus():
    with conectar() as conn:
        return conn.execute("SELECT * FROM campus ORDER BY nome").fetchall()


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


def listar_turmas():
    with conectar() as conn:
        return conn.execute("""
            SELECT t.id_turma, t.nome, t.curso, t.ano, c.nome
            FROM turmas t
            INNER JOIN campus c ON c.id_campus = t.campus_id
            ORDER BY t.nome
        """).fetchall()


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
# REFEIÇÕES
# ======================================================

def registrar_refeicao(aluno_id, tipo="ALMOCO"):
    agora = datetime.now()
    data = agora.strftime("%Y-%m-%d")
    hora = agora.strftime("%H:%M:%S")
    with conectar() as conn:
        conn.execute(
            "INSERT INTO refeicoes(aluno_id,data,hora,tipo) VALUES(?,?,?,?)",
            (aluno_id, data, hora, tipo)
        )
        conn.commit()


def listar_refeicoes():
    with conectar() as conn:
        return conn.execute("""
            SELECT a.nome, a.matricula, r.data, r.hora, r.tipo
            FROM refeicoes r
            INNER JOIN alunos a ON r.aluno_id = a.id_aluno
            ORDER BY r.data DESC, r.hora DESC
        """).fetchall()


def listar_refeicoes_hoje():
    hoje = datetime.now().strftime("%Y-%m-%d")
    with conectar() as conn:
        return conn.execute("""
            SELECT a.nome, a.matricula, r.hora
            FROM refeicoes r
            INNER JOIN alunos a ON r.aluno_id = a.id_aluno
            WHERE r.data=?
            ORDER BY r.hora
        """, (hoje,)).fetchall()


def aluno_ja_almocou_hoje(aluno_id):
    hoje = datetime.now().strftime("%Y-%m-%d")
    with conectar() as conn:
        cursor = conn.execute("""
            SELECT COUNT(*) FROM refeicoes
            WHERE aluno_id = ? AND data = ?
        """, (aluno_id, hoje))
        return cursor.fetchone()[0] > 0


def listar_refeicoes_periodo(data_inicial, data_final):
    with conectar() as conn:
        return conn.execute("""
            SELECT a.matricula, a.nome, t.nome, r.data, r.hora
            FROM refeicoes r
            INNER JOIN alunos a ON r.aluno_id = a.id_aluno
            INNER JOIN turmas t ON a.turma_id = t.id_turma
            WHERE r.data BETWEEN ? AND ?
            ORDER BY r.data, r.hora
        """, (data_inicial, data_final)).fetchall()


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
                   b.tipo, b.valor, b.data_inicio, b.data_fim, b.ativo
            FROM beneficios b
            INNER JOIN alunos a ON b.aluno_id = a.id_aluno
            ORDER BY b.ativo DESC, b.data_inicio DESC
        """).fetchall()


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

def stats_refeicoes_por_dia(dias=30):
    with conectar() as conn:
        return conn.execute("""
            SELECT data, COUNT(*) AS total
            FROM refeicoes
            WHERE data >= date('now', ? || ' days')
            GROUP BY data
            ORDER BY data
        """, (f'-{dias}',)).fetchall()


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


# ======================================================
# INICIALIZAÇÃO
# ======================================================

if __name__ == "__main__":
    criar_tabelas()
    print("=" * 50)
    print("BANCO DE DADOS CRIADO COM SUCESSO!")
    print(f"Arquivo: {CAMINHO_BANCO}")
    print("=" * 50)