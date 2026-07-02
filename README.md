# SocioEstudantil

Sistema de gestão da assistência estudantil do **IFAM Campus Humaitá** (Instituto Federal do Amazonas). Permite acompanhar distribuição de refeições, perfis socioeconômicos e benefícios financeiros dos alunos conforme os critérios do PNAES.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Tecnologias](#tecnologias)
- [Funcionalidades](#funcionalidades)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Banco de Dados](#banco-de-dados)
- [Instalação e Execução](#instalação-e-execução)
- [Rotas da Aplicação](#rotas-da-aplicação)
- [Automação (BotCity)](#automação-botcity)
- [Regras de Negócio](#regras-de-negócio)

---

## Visão Geral

O SocioEstudantil é uma aplicação web Django voltada ao setor de assistência estudantil. Centraliza três processos principais:

1. **Controle de refeições** — registro via matrícula/leitura de crachá, com bloqueio de duplicatas no mesmo dia.
2. **Perfil socioeconômico** — cadastro de renda familiar, composição familiar e situação de moradia para identificar alunos em vulnerabilidade social (critério PNAES).
3. **Gestão de benefícios** — administração de auxílios de transporte e moradia com histórico e controle de vigência.

---

## Tecnologias

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend | Django | 6.0.6 |
| Banco de dados | SQLite3 | — |
| Geração de PDF | ReportLab | 5.0.0 |
| Processamento de imagem | Pillow | 12.2.0 |
| CSS / Layout | Bootstrap | 5.3.8 |
| Ícones | Bootstrap Icons | 1.11.3 |
| Gráficos | Chart.js | 4.4.4 |
| Automação (RPA) | BotCity | 1.1.0 |

---

## Funcionalidades

### Painel (`/painel/`)
- Cards com KPIs: total de alunos ativos, refeições servidas hoje, alunos com perfil cadastrado e alunos em vulnerabilidade.
- Gráfico de barras com refeições nos últimos 30 dias.
- Gráfico de rosca com distribuição de benefícios ativos.

### Lista de Alunos (`/alunos/`)
- Tabela com nome, matrícula e turma.
- Acesso rápido ao perfil individual.
- Importação em massa via CSV.

### Perfil do Aluno (`/alunos/<id>/perfil/`)
- Cadastro e edição de dados socioeconômicos (renda, membros da família, situação de moradia).
- Cálculo automático da renda per capita e classificação de vulnerabilidade.
- Listagem dos benefícios ativos do aluno.

### Leitor de Refeições (`/leitor/`)
- Campo de entrada para matrícula (compatível com leitura de código de barras / crachá).
- Retorno visual imediato:
  - **Verde** — refeição registrada com sucesso.
  - **Amarelo** — refeição já registrada hoje.
  - **Vermelho** — aluno não encontrado.

### Benefícios (`/beneficios/`)
- Cadastro, edição e encerramento de benefícios (TRANSPORTE, MORADIA).
- Campos: aluno, tipo, valor (R$), período de vigência e observações.
- Filtro entre benefícios ativos e encerrados.

### Relatórios PDF (`/relatorio-pdf/`)
Três modelos de relatório com cabeçalho IFAM e data de geração:
- **Refeições** — registros por período.
- **Benefícios Ativos** — auxílios vigentes com valores e períodos.
- **Alunos em Vulnerabilidade** — alunos que atendem ao critério PNAES.

### Importação CSV (`/importar/`)
- Cadastro em lote de alunos a partir de arquivo CSV.
- Colunas esperadas: `matricula`, `nome`, `turma`.
- Cria turmas automaticamente caso não existam; ignora matrículas duplicadas.

---

## Estrutura do Projeto

```
SOCIOESTUDANTIL/
├── manage.py                    # Ponto de entrada Django
├── requirements.txt             # Dependências Python
│
├── src/
│   └── banco.py                 # Camada de acesso ao banco (50+ funções)
│
├── teste/                       # Pacote Django principal
│   ├── settings.py              # Configurações
│   ├── urls.py                  # Roteamento de URLs
│   ├── views.py                 # Lógica das views (~316 linhas)
│   └── templatetags/
│       └── dict_extras.py       # Filtro customizado get_item
│
├── templates/                   # Templates HTML
│   ├── base.html                # Layout base e navegação
│   ├── home.html                # Página inicial
│   ├── painel.html              # Dashboard com gráficos
│   ├── alunos.html              # Lista de alunos
│   ├── perfil.html              # Perfil e benefícios do aluno
│   ├── beneficios.html          # CRUD de benefícios
│   ├── leitor.html              # Scanner de refeições
│   ├── importar.html            # Importação CSV
│   ├── relatorio.html           # Exportação CSV (legado)
│   └── relatorio_pdf.html       # Gerador de PDF
│
├── static/
│   └── ifam_humaita_logo_inicio.png
│
├── dados/
│   └── banco_ticket.db          # Banco de dados SQLite
│
└── automacoes/                  # Bots RPA (BotCity)
    ├── requirements.txt         # Dependências dos bots (separadas da aplicação)
    ├── bot_relatorio_vulneraveis.py
    └── relatorios/              # PDFs gerados pelos bots
```

---

## Banco de Dados

O banco SQLite fica em `dados/banco_ticket.db` e é gerenciado diretamente pela camada `src/banco.py` (sem uso do ORM do Django).

### Tabelas

| Tabela | Descrição |
|--------|-----------|
| `campus` | Campi cadastrados (nome, sigla) |
| `turmas` | Turmas/cursos por campus e ano |
| `alunos` | Alunos com matrícula única vinculada a turma |
| `refeicoes` | Registro de refeições (aluno, data, hora, tipo) |
| `perfil_socioeconomico` | Renda familiar, membros, situação de moradia |
| `beneficios` | Auxílios financeiros com período de vigência |

### Diagrama simplificado

```
campus ──< turmas ──< alunos ──< refeicoes
                                 alunos ──< perfil_socioeconomico (1:1)
                                 alunos ──< beneficios
```

---

## Instalação e Execução

### Pré-requisitos
- Python 3.10+

### Passos

```powershell
# 1. Criar e ativar ambiente virtual
python -m venv venv
venv\Scripts\Activate.ps1

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Inicializar as tabelas do banco (apenas na primeira vez)
python -c "from src.banco import criar_tabelas; criar_tabelas()"

# 4. Iniciar o servidor
python manage.py runserver
```

Acesse em: [http://localhost:8000](http://localhost:8000)

---

## Rotas da Aplicação

| Rota | Descrição |
|------|-----------|
| `/` | Página inicial |
| `/painel/` | Dashboard com KPIs e gráficos |
| `/alunos/` | Lista de alunos |
| `/alunos/<id>/perfil/` | Perfil socioeconômico do aluno |
| `/leitor/` | Scanner de refeições |
| `/beneficios/` | Gestão de benefícios |
| `/relatorio/` | Exportação CSV de refeições (legado) |
| `/relatorio-pdf/` | Gerador de relatórios PDF |
| `/importar/` | Importação de alunos via CSV |
| `/admin/` | Painel administrativo Django |

---

## Automação (BotCity)

O diretório `automacoes/` contém bots RPA construídos com [BotCity](https://botcity.dev/) que operam a aplicação pela própria interface web (como um operador faria), já que o sistema não expõe API.

### `bot_relatorio_vulneraveis.py`

Gera automaticamente o **Relatório de Alunos em Situação de Vulnerabilidade** (PDF):

1. Abre o Chrome e navega até `/relatorio-pdf/`.
2. Clica no botão "Gerar PDF" do card "Alunos vulneráveis".
3. Aguarda o download e salva o arquivo em `automacoes/relatorios/vulneraveis_AAAA-MM-DD.pdf`.

**Pré-requisitos**
- Servidor Django rodando (`python manage.py runserver`).
- Google Chrome instalado.
- Dependências do bot já incluídas no `requirements.txt` da raiz (um único `pip install -r requirements.txt` instala tudo, aplicação e bots).

**Execução**
```powershell
venv\Scripts\python.exe automacoes\bot_relatorio_vulneraveis.py
```
Por padrão o bot roda com o Chrome **visível**, para acompanhar cada passo. Para rodar escondido (ex.: agendado em servidor), defina a variável de ambiente antes:
```powershell
$env:SOCIOESTUDANTIL_HEADLESS = "true"
venv\Scripts\python.exe automacoes\bot_relatorio_vulneraveis.py
```

A URL da aplicação pode ser customizada via `SOCIOESTUDANTIL_URL` (padrão `http://localhost:8000`).

**Nota técnica**: em Python 3.12+ o módulo `distutils` foi removido, mas uma dependência do BotCity (`undetected-chromedriver`) ainda o importa — o script contorna isso importando `setuptools` antes do `botcity.web`. O chromedriver correspondente à versão do Chrome instalado é baixado automaticamente via `webdriver-manager`.

### Próximas automações planejadas
- Envio automático do PDF gerado por e-mail.
- Agendamento periódico (mensal) via Agendador de Tarefas do Windows ou BotCity Maestro.
- Mesmo padrão aplicado aos relatórios de refeições e benefícios ativos.

---

## Regras de Negócio

### Vulnerabilidade Social (PNAES)

Um aluno é considerado **em situação de vulnerabilidade** quando sua renda per capita familiar for menor ou igual a 1,5 salário mínimo:

```
renda_per_capita = renda_familiar / num_membros
vulneravel = renda_per_capita <= salario_minimo * 1.5
```

Valor de referência (2025): **R$ 1.518,00** × 1,5 = **R$ 2.277,00**

### Controle de Refeições

- Apenas uma refeição por aluno por dia é permitida.
- Tentativas duplicadas retornam aviso sem criar novo registro.
- O tipo padrão de refeição é `ALMOCO`.

### Situações de Moradia

| Código | Descrição |
|--------|-----------|
| `PROPRIA` | Residência própria |
| `ALUGADA` | Residência alugada |
| `CEDIDA` | Residência cedida |
| `QUILOMBOLA` | Comunidade quilombola |
| `NAO_INFORMADO` | Não informado |

### Tipos de Benefício

| Código | Descrição |
|--------|-----------|
| `TRANSPORTE` | Auxílio transporte |
| `MORADIA` | Auxílio moradia |
