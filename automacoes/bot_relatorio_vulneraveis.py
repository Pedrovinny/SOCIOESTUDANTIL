"""
Bot BotCity que gera o relatório PDF de "Alunos em Situação de Vulnerabilidade"
navegando pela tela /relatorio-pdf/ do sistema SocioEstudantil, como um operador faria.

Pré-requisito: o servidor Django precisa estar rodando (python manage.py runserver).
"""
import os
from datetime import datetime

# Precisa ser importado antes do botcity: o Python 3.12+ removeu o módulo `distutils`,
# do qual o undetected-chromedriver ainda depende. Importar setuptools primeiro
# restaura o módulo em sys.modules antes que o botcity tente usá-lo.
import setuptools  # noqa: F401

from botcity.web import WebBot, Browser, By
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = os.environ.get("SOCIOESTUDANTIL_URL", "http://localhost:8000")
RELATORIOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relatorios")


def gerar_relatorio_vulneraveis():
    os.makedirs(RELATORIOS_DIR, exist_ok=True)

    # SOCIOESTUDANTIL_HEADLESS=true esconde a janela (uso em servidor/agendador).
    # Por padrao roda com a janela visivel, para acompanhar o bot navegando.
    headless = os.environ.get("SOCIOESTUDANTIL_HEADLESS", "false").lower() == "true"

    bot = WebBot()
    bot.browser = Browser.CHROME
    bot.headless = headless
    bot.download_folder_path = RELATORIOS_DIR
    bot.driver_path = ChromeDriverManager().install()

    try:
        bot.browse(f"{BASE_URL}/relatorio-pdf/")
        bot.wait(1500)  # pausa so para dar tempo de ver a pagina carregada

        arquivos_antes = bot.get_file_count(RELATORIOS_DIR, ".pdf")

        botao = bot.find_element(
            "//input[@name='tipo_relatorio' and @value='vulneraveis']/ancestor::form//button",
            By.XPATH,
        )
        botao.click()

        novo_arquivo = bot.wait_for_new_file(
            RELATORIOS_DIR, file_extension=".pdf", current_count=arquivos_antes, timeout=30000
        )
        if not novo_arquivo:
            raise RuntimeError("O PDF nao foi baixado dentro do tempo esperado.")

        destino = os.path.join(RELATORIOS_DIR, f"vulneraveis_{datetime.now():%Y-%m-%d}.pdf")
        os.replace(novo_arquivo, destino)
        print(f"Relatorio gerado com sucesso: {destino}")

        if not headless:
            bot.wait(2000)  # deixa a janela aberta mais um pouco antes de fechar
        return destino
    finally:
        bot.stop_browser()


if __name__ == "__main__":
    gerar_relatorio_vulneraveis()
