"""
Bot BotCity que gera os relatórios PDF de /relatorio-pdf/ e envia por e-mail
(Mailtrap SMTP) aos endereços cadastrados em /inscricoes/, conforme a
frequência (DIARIA, SEMANAL ou MENSAL) informada na linha de comando.

Substitui o antigo bot_relatorio_vulneraveis.py: em vez de baixar um único
relatório fixo, ele lê as inscrições no banco (src/banco.py), baixa só os
tipos de relatório realmente necessários e envia cada e-mail com os anexos
que aquele inscrito escolheu.

Pré-requisitos:
- Servidor Django rodando (python manage.py runserver).
- MAILTRAP_API_TOKEN e DEFAULT_FROM_EMAIL configurados (ver README, seção
  "Envio de E-mail (Mailtrap SMTP)").
- Pelo menos uma inscrição cadastrada em /inscricoes/ com a frequência
  informada.

Uso:
    venv\\Scripts\\python.exe automacoes\\bot_envio_relatorios.py --frequencia DIARIA
    venv\\Scripts\\python.exe automacoes\\bot_envio_relatorios.py --frequencia SEMANAL
    venv\\Scripts\\python.exe automacoes\\bot_envio_relatorios.py --frequencia MENSAL

Pensado para ser chamado por 3 tarefas separadas no Agendador de Tarefas do
Windows (uma por frequência), cada uma dessa acionando o horário desejado.
"""
import argparse
import os
import sys
from datetime import datetime

# Precisa ser importado antes do botcity: o Python 3.12+ removeu o módulo `distutils`,
# do qual o undetected-chromedriver ainda depende. Importar setuptools primeiro
# restaura o módulo em sys.modules antes que o botcity tente usá-lo.
import setuptools  # noqa: F401

from botcity.web import WebBot, Browser, By
from webdriver_manager.chrome import ChromeDriverManager

# Permite importar `src` e `teste.settings` mesmo rodando o script de dentro
# de automacoes/ (fora da raiz do projeto).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teste.settings")
import django  # noqa: E402
django.setup()

from django.core.mail import EmailMultiAlternatives  # noqa: E402
from django.template.loader import render_to_string  # noqa: E402
from src.banco import listar_inscricoes_email, FREQUENCIAS_ENVIO, TIPOS_RELATORIO  # noqa: E402

BASE_URL = os.environ.get("SOCIOESTUDANTIL_URL", "http://localhost:8000")
RELATORIOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relatorios")


def baixar_relatorio(bot, tipo_relatorio):
    """Clica no botão 'Gerar PDF' do card do tipo informado e retorna o caminho do PDF baixado."""
    arquivos_antes = bot.get_file_count(RELATORIOS_DIR, ".pdf")

    botao = bot.find_element(
        f"//input[@name='tipo_relatorio' and @value='{tipo_relatorio}']/ancestor::form//button",
        By.XPATH,
    )
    botao.click()

    novo_arquivo = bot.wait_for_new_file(
        RELATORIOS_DIR, file_extension=".pdf", current_count=arquivos_antes, timeout=30000
    )
    if not novo_arquivo:
        raise RuntimeError(f"O PDF de '{tipo_relatorio}' nao foi baixado dentro do tempo esperado.")

    destino = os.path.join(RELATORIOS_DIR, f"{tipo_relatorio}_{datetime.now():%Y-%m-%d}.pdf")
    os.replace(novo_arquivo, destino)
    return destino


def enviar_email(destinatario, frequencia, tipos, anexos):
    nomes = [TIPOS_RELATORIO[t] for t in tipos]
    data = datetime.now().strftime("%d/%m/%Y")
    frequencia_label = FREQUENCIAS_ENVIO.get(frequencia, frequencia).lower()

    assunto = f"Relatórios SocioEstudantil — {data}"

    corpo_texto = (
        "Olá,\n\n"
        f"Segue(m) em anexo o(s) relatório(s) com frequência {frequencia_label}, gerado(s) em {data}:\n\n"
        + "\n".join(f"- {nome}" for nome in nomes)
        + "\n\nPara alterar quais relatórios recebe ou a frequência de envio, acesse "
        f"{BASE_URL}/inscricoes/.\n\n"
        "Assistência Estudantil — IFAM Campus Humaitá"
    )
    corpo_html = render_to_string("email/relatorio_email.html", {
        "nomes": nomes,
        "data": data,
        "frequencia_label": frequencia_label,
        "base_url": BASE_URL,
    })

    email = EmailMultiAlternatives(assunto, corpo_texto, to=[destinatario])
    email.attach_alternative(corpo_html, "text/html")
    for caminho in anexos:
        email.attach_file(caminho)
    email.send()


def enviar_relatorios(frequencia):
    os.makedirs(RELATORIOS_DIR, exist_ok=True)

    inscricoes = [
        (email, [t for t in tipos_str.split(",") if t in TIPOS_RELATORIO])
        for _, email, freq, tipos_str, _ in listar_inscricoes_email()
        if freq == frequencia and tipos_str
    ]
    if not inscricoes:
        print(f"Nenhuma inscrição cadastrada para a frequência {frequencia}.")
        return

    tipos_necessarios = sorted({tipo for _, tipos in inscricoes for tipo in tipos})

    headless = os.environ.get("SOCIOESTUDANTIL_HEADLESS", "false").lower() == "true"
    bot = WebBot()
    bot.browser = Browser.CHROME
    bot.headless = headless
    bot.download_folder_path = RELATORIOS_DIR
    bot.driver_path = ChromeDriverManager().install()

    try:
        bot.browse(f"{BASE_URL}/relatorio-pdf/")
        bot.wait(1500)  # pausa so para dar tempo de ver a pagina carregada

        caminhos = {}
        for tipo in tipos_necessarios:
            print(f"Gerando relatório: {TIPOS_RELATORIO[tipo]}...")
            caminhos[tipo] = baixar_relatorio(bot, tipo)

        enviados = 0
        for email, tipos in inscricoes:
            anexos = [caminhos[t] for t in tipos if t in caminhos]
            if not anexos:
                continue
            print(f"Enviando para {email}: {', '.join(TIPOS_RELATORIO[t] for t in tipos)}")
            enviar_email(email, frequencia, tipos, anexos)
            enviados += 1

        if not headless:
            bot.wait(2000)  # deixa a janela aberta mais um pouco antes de fechar

        print(f"Concluído: {enviados} e-mail(s) enviado(s) para a frequência {frequencia}.")
    finally:
        bot.stop_browser()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera e envia por e-mail os relatórios PDF das inscrições de uma frequência."
    )
    parser.add_argument(
        "--frequencia", required=True, choices=["DIARIA", "SEMANAL", "MENSAL"],
        help="Frequência de envio a processar nesta execução.",
    )
    args = parser.parse_args()
    enviar_relatorios(args.frequencia)
