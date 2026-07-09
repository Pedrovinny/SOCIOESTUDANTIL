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
- [Envio de E-mail (Mailtrap SMTP)](#envio-de-e-mail-mailtrap-smtp)
- [Automação (BotCity)](#automação-botcity)
- [Regras de Negócio](#regras-de-negócio)

---

## Visão Geral

O SocioEstudantil é uma aplicação web Django voltada ao setor de assistência estudantil. Centraliza três processos principais:

1. **Controle de refeições** — registro e acompanhamento das refeições servidas, com bloqueio de duplicatas no mesmo dia.
2. **Perfil socioeconômico** — cadastro de renda familiar, composição familiar e situação de moradia para identificar alunos em vulnerabilidade social (critério PNAES).
3. **Gestão de benefícios** — administração de auxílios de transporte e moradia com histórico e controle de vigência.

---

## Tecnologias

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend | Django | 6.0.6 |
| Banco de dados | SQLite3 | — |
| Geração de PDF | ReportLab | 5.0.0 |
| CSS / Layout | Bootstrap | 5.3.8 |
| Ícones | Bootstrap Icons | 1.11.3 |
| Gráficos | Chart.js | 4.4.4 |
| Envio de e-mail | Mailtrap SMTP | — |
| Automação (RPA) | BotCity | 1.1.0 |

---

## Funcionalidades

### Painel (`/painel/`)
- Cards com KPIs: total de alunos ativos, refeições servidas hoje, alunos com perfil cadastrado e alunos em vulnerabilidade.
- Gráfico cruzado de vulnerabilidade x cobertura de benefícios (quantos alunos vulneráveis já recebem algum auxílio e quantos ainda não).
- Gráfico de rosca com distribuição de benefícios ativos por tipo (quantidade e valor em R$).
- Gráfico de barras com alunos por turma.
- Gráfico de rosca com distribuição por situação de moradia.

### Lista de Alunos (`/alunos/`)
- Tabela com nome, matrícula e turma.
- Acesso rápido ao perfil individual.
- Importação em massa via CSV.

### Perfil do Aluno (`/alunos/<id>/perfil/`)
- Cadastro e edição de dados socioeconômicos (renda, membros da família, situação de moradia).
- Cálculo automático da renda per capita e classificação de vulnerabilidade.
- Listagem dos benefícios ativos do aluno.

### Benefícios (`/beneficios/`)
- Cadastro, edição e encerramento de benefícios (TRANSPORTE, MORADIA).
- Campos: aluno, tipo, valor (R$), período de vigência e observações.
- Filtro entre benefícios ativos e encerrados.

### Relatórios PDF (`/relatorio-pdf/`)
Cinco modelos de relatório com cabeçalho IFAM e data de geração:
- **Benefícios Ativos** — auxílios vigentes com valores e períodos.
- **Alunos em Vulnerabilidade** — alunos que atendem ao critério PNAES.
- **Alunos por Turma** — quantidade de alunos ativos em cada turma.
- **Sem Perfil Cadastrado** — alunos ativos que ainda não têm perfil socioeconômico preenchido.
- **Vulneráveis sem Benefício** — cruza vulnerabilidade com benefícios ativos: lista de prioridade para atendimento.

### Importação CSV (`/importar/`)
- Cadastro em lote de alunos a partir de arquivo CSV.
- Colunas esperadas: `matricula`, `nome`, `turma`.
- Botão para baixar um modelo de CSV preenchido com o cabeçalho correto (`/importar/modelo/`).
- Cria turmas automaticamente caso não existam; ignora matrículas duplicadas.

### Inscrições de E-mail (`/inscricoes/`)
- Cadastro de e-mails para recebimento periódico de relatórios.
- Frequência de envio (Diária, Semanal ou Mensal).
- Seleção de quais relatórios (entre os 5 gerados em `/relatorio-pdf/`) cada e-mail deve receber.
- O envio em si é feito pelo bot `automacoes/bot_envio_relatorios.py` (ver seção [Automação (BotCity)](#automação-botcity)).

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
│   ├── importar.html            # Importação CSV
│   ├── relatorio_pdf.html       # Gerador de PDF
│   └── inscricoes.html          # Cadastro de e-mails para relatórios periódicos
│
├── static/
│   └── ifam_humaita_logo_inicio.png
│
├── dados/
│   └── banco.db                 # Banco de dados SQLite
│
└── automacoes/                  # Bots RPA (BotCity)
    ├── bot_envio_relatorios.py  # Gera os PDFs e envia por e-mail às inscrições
    └── relatorios/              # PDFs gerados pelo bot
```

---

## Banco de Dados

O banco SQLite fica em `dados/banco.db` e é gerenciado diretamente pela camada `src/banco.py` (sem uso do ORM do Django).

### Tabelas

| Tabela | Descrição |
|--------|-----------|
| `campus` | Campi cadastrados (nome, sigla) |
| `turmas` | Turmas/cursos por campus e ano |
| `alunos` | Alunos com matrícula única vinculada a turma |
| `refeicoes` | Registro de refeições (aluno, data, hora, tipo) |
| `perfil_socioeconomico` | Renda familiar, membros, situação de moradia |
| `beneficios` | Auxílios financeiros com período de vigência |
| `inscricoes_email` | E-mails cadastrados para recebimento periódico de relatórios |

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
| `/beneficios/` | Gestão de benefícios |
| `/relatorio-pdf/` | Gerador de relatórios PDF |
| `/importar/` | Importação de alunos via CSV |
| `/importar/modelo/` | Download do modelo de CSV para importação |
| `/inscricoes/` | Cadastro de e-mails para relatórios periódicos |
| `/admin/` | Painel administrativo Django |

---

## Envio de E-mail (Mailtrap SMTP)

O envio de e-mail é feito via SMTP do Mailtrap (`teste/settings.py`), usando o backend padrão do Django (`django.core.mail`).

### Configuração

1. Crie um API Token em [Settings → API Tokens](https://mailtrap.io/settings/api-tokens) no Mailtrap (acesso Admin).
2. Defina a variável de ambiente com o token **antes** de rodar o servidor:

```powershell
$env:MAILTRAP_API_TOKEN = "seu_token_aqui"
python manage.py runserver
```

3. Em `teste/settings.py`, ajuste `DEFAULT_FROM_EMAIL` para um endereço do seu **domínio verificado** no Mailtrap (Sending Domains) — sem isso o envio falha mesmo com o token correto.

### Testar o envio

Sem escrever nenhum código, usando o comando embutido do Django:

```powershell
python manage.py sendtestemail seu-email@exemplo.com
```

Depois de enviar, confira os e-mails em [mailtrap.io/sending/email_logs](https://mailtrap.io/sending/email_logs).

### Uso no código

Com as settings configuradas, qualquer view pode enviar e-mail com a API padrão do Django:

```python
from django.core.mail import send_mail

send_mail(
    "Assunto",
    "Corpo da mensagem.",
    None,  # usa DEFAULT_FROM_EMAIL
    ["destinatario@exemplo.com"],
)
```

---

## Automação (BotCity)

O diretório `automacoes/` contém bots RPA construídos com [BotCity](https://botcity.dev/) que operam a aplicação pela própria interface web (como um operador faria), já que o sistema não expõe API.

### `bot_envio_relatorios.py`

Gera os relatórios PDF de `/relatorio-pdf/` e envia por e-mail (Mailtrap SMTP) aos endereços cadastrados em `/inscricoes/`, respeitando a frequência informada na linha de comando:

1. Lê em `inscricoes_email` (via `src/banco.py`) quem está inscrito na frequência pedida e quais relatórios cada um escolheu.
2. Abre o Chrome, navega até `/relatorio-pdf/` e clica em "Gerar PDF" — uma vez por tipo de relatório realmente necessário (nunca gera o mesmo PDF duas vezes, mesmo com vários inscritos pedindo o mesmo relatório).
3. Salva cada PDF em `automacoes/relatorios/<tipo>_AAAA-MM-DD.pdf`.
4. Envia um e-mail por inscrito, anexando só os relatórios que ele escolheu, usando as settings de e-mail do Django (mesma configuração da seção [Envio de E-mail](#envio-de-e-mail-mailtrap-smtp)).

**Pré-requisitos**
- Servidor Django rodando (`python manage.py runserver`).
- Google Chrome instalado.
- `MAILTRAP_API_TOKEN` definido e `DEFAULT_FROM_EMAIL` configurado (seção [Envio de E-mail](#envio-de-e-mail-mailtrap-smtp)).
- Pelo menos uma inscrição cadastrada em `/inscricoes/` com a frequência que for executada.
- Dependências do bot já incluídas no `requirements.txt` da raiz (um único `pip install -r requirements.txt` instala tudo, aplicação e bots).

**Execução**

O parâmetro `--frequencia` é obrigatório — cada execução processa só as inscrições daquela frequência:
```powershell
venv\Scripts\python.exe automacoes\bot_envio_relatorios.py --frequencia DIARIA
venv\Scripts\python.exe automacoes\bot_envio_relatorios.py --frequencia SEMANAL
venv\Scripts\python.exe automacoes\bot_envio_relatorios.py --frequencia MENSAL
```

Por padrão o bot roda com o Chrome **visível**, para acompanhar cada passo. Para rodar escondido (ex.: agendado em servidor), defina a variável de ambiente antes:
```powershell
$env:SOCIOESTUDANTIL_HEADLESS = "true"
venv\Scripts\python.exe automacoes\bot_envio_relatorios.py --frequencia MENSAL
```

A URL da aplicação pode ser customizada via `SOCIOESTUDANTIL_URL` (padrão `http://localhost:8000`).

**Agendamento**: crie 3 tarefas no Agendador de Tarefas do Windows (uma para cada frequência), cada uma chamando o comando acima com o `--frequencia` e o horário/recorrência correspondente (ex.: a tarefa `SEMANAL` rodando toda segunda-feira).

**Nota técnica**: em Python 3.12+ o módulo `distutils` foi removido, mas uma dependência do BotCity (`undetected-chromedriver`) ainda o importa — o script contorna isso importando `setuptools` antes do `botcity.web`. O chromedriver correspondente à versão do Chrome instalado é baixado automaticamente via `webdriver-manager`. O bot também inicializa as settings do Django (`django.setup()`) só para reaproveitar a configuração de e-mail — ele não usa o ORM, os dados de inscrições são lidos via `src/banco.py` (SQL puro).

---

## Regras de Negócio

### Vulnerabilidade Social (PNAES)

Um aluno é considerado **em situação de vulnerabilidade** quando sua renda per capita familiar for menor ou igual a 1,5 salário mínimo:

```
renda_per_capita = renda_familiar / num_membros
vulneravel = renda_per_capita <= salario_minimo * 1.5
```

Valor de referência (2025): **R$ 1.518,00** × 1,5 = **R$ 2.277,00**

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
