from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings
from src.banco import *

import csv
import io
import json
import os
import sqlite3

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


# ======================================================
# PÁGINAS EXISTENTES (sem alteração de lógica)
# ======================================================

def home(request):
    return render(request, "home.html")


def importar_csv(request):
    mensagem = ""
    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        if arquivo:
            texto = io.StringIO(arquivo.read().decode("utf-8-sig"))
            leitor = csv.DictReader(texto)
            total = 0
            for linha in leitor:
                matricula = linha["matricula"].strip()
                nome      = linha["nome"].strip()
                turma     = linha["turma"].strip()
                turma_id  = buscar_turma_nome(turma)
                if turma_id is None:
                    inserir_turma(nome=turma, curso="", ano=2026, campus_id=1)
                    turma_id = buscar_turma_nome(turma)
                if buscar_aluno_matricula(matricula) is None:
                    inserir_aluno(nome, matricula, turma_id)
                    total += 1
            mensagem = f"{total} alunos importados com sucesso."
    return render(request, "importar.html", {"mensagem": mensagem})


def modelo_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="modelo_importacao_alunos.csv"'
    writer = csv.writer(response)
    writer.writerow(["matricula", "nome", "turma"])
    writer.writerow(["2024001", "João da Silva", "1º Ano Informática"])
    writer.writerow(["2024002", "Maria Oliveira", "1º Ano Informática"])
    return response


# ======================================================
# ALUNOS
# ======================================================

def listar_alunos_view(request):
    alunos = listar_alunos()
    return render(request, "alunos.html", {"alunos": alunos})


# ======================================================
# PERFIL SOCIOECONÔMICO
# ======================================================

def perfil(request, aluno_id):
    aluno = buscar_aluno_id(aluno_id)
    if not aluno:
        return redirect("listar_alunos")

    perfil_atual = buscar_perfil_aluno(aluno_id)
    mensagem = ""

    if request.method == "POST":
        renda   = float(request.POST.get("renda_familiar", 0) or 0)
        membros = int(request.POST.get("num_membros", 1) or 1)
        moradia = request.POST.get("situacao_moradia", "NAO_INFORMADO")
        obs     = request.POST.get("observacoes", "")
        salvar_perfil(aluno_id, renda, membros, moradia, obs)
        mensagem     = "Perfil salvo com sucesso."
        perfil_atual = buscar_perfil_aluno(aluno_id)

    renda_pc   = 0.0
    vulneravel = False
    if perfil_atual:
        renda_pc   = calcular_renda_per_capita(perfil_atual[2], perfil_atual[3])
        vulneravel = calcular_vulnerabilidade(renda_pc)

    beneficios_aluno = listar_beneficios_aluno(aluno_id)

    return render(request, "perfil.html", {
        "aluno":            aluno,
        "perfil":           perfil_atual,
        "renda_pc":         round(renda_pc, 2),
        "vulneravel":       vulneravel,
        "situacoes":        SITUACOES_MORADIA,
        "mensagem":         mensagem,
        "beneficios_aluno": beneficios_aluno,
        "tipos_beneficio":  TIPOS_BENEFICIO,
    })


# ======================================================
# BENEFÍCIOS
# ======================================================

def beneficios(request):
    mensagem = ""
    alunos   = listar_alunos()
    lista    = listar_beneficios()

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "inserir":
            aluno_id    = int(request.POST["aluno_id"])
            tipo        = request.POST["tipo"]
            valor       = float(request.POST.get("valor", 0) or 0)
            data_inicio = request.POST["data_inicio"]
            data_fim    = request.POST.get("data_fim") or None
            obs         = request.POST.get("observacoes", "")
            inserir_beneficio(aluno_id, tipo, valor, data_inicio, data_fim, obs)
            mensagem = "Benefício cadastrado com sucesso."

        elif acao == "editar":
            id_beneficio = int(request.POST["id_beneficio"])
            aluno_id     = int(request.POST["aluno_id"])
            tipo         = request.POST["tipo"]
            valor        = float(request.POST.get("valor", 0) or 0)
            data_inicio  = request.POST["data_inicio"]
            data_fim     = request.POST.get("data_fim") or None
            obs          = request.POST.get("observacoes", "")
            editar_beneficio(id_beneficio, aluno_id, tipo, valor, data_inicio, data_fim, obs)
            mensagem = "Benefício atualizado com sucesso."

        elif acao == "encerrar":
            id_beneficio = int(request.POST["id_beneficio"])
            encerrar_beneficio(id_beneficio)
            mensagem = "Benefício encerrado."

        lista = listar_beneficios()

    return render(request, "beneficios.html", {
        "lista":    lista,
        "alunos":   alunos,
        "tipos":    TIPOS_BENEFICIO,
        "mensagem": mensagem,
    })


# ======================================================
# INSCRIÇÕES DE E-MAIL
# ======================================================

def inscricoes_email(request):
    mensagem = ""
    erro = ""

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "inserir":
            email           = request.POST.get("email", "").strip()
            frequencia      = request.POST.get("frequencia", "SEMANAL")
            tipos_relatorio = request.POST.getlist("tipos_relatorio")

            if not tipos_relatorio:
                erro = "Selecione ao menos um tipo de relatório."
            else:
                try:
                    validate_email(email)
                    inserir_inscricao_email(email, frequencia, tipos_relatorio)
                    mensagem = "E-mail cadastrado com sucesso."
                except ValidationError:
                    erro = "Informe um e-mail válido."
                except sqlite3.IntegrityError:
                    erro = "Este e-mail já está cadastrado."

        elif acao == "excluir":
            id_inscricao = int(request.POST["id_inscricao"])
            excluir_inscricao_email(id_inscricao)
            mensagem = "Inscrição removida."

    lista = []
    for id_insc, email, freq, tipos_str, data_cad in listar_inscricoes_email():
        tipos_label = ", ".join(
            TIPOS_RELATORIO.get(t, t) for t in tipos_str.split(",") if t
        )
        lista.append((id_insc, email, FREQUENCIAS_ENVIO.get(freq, freq), tipos_label, data_cad))

    return render(request, "inscricoes.html", {
        "lista":       lista,
        "frequencias": FREQUENCIAS_ENVIO,
        "tipos":       TIPOS_RELATORIO,
        "mensagem":    mensagem,
        "erro":        erro,
    })


# ======================================================
# PAINEL
# ======================================================

def painel(request):
    beneficios_ativos = stats_beneficios_ativos()
    labels_ben        = [TIPOS_BENEFICIO.get(b[0], b[0]) for b in beneficios_ativos]
    dados_ben_qtd     = [b[1] for b in beneficios_ativos]
    dados_ben_valor   = [round(b[2] or 0, 2) for b in beneficios_ativos]

    turmas_alunos  = stats_alunos_por_turma()
    labels_turma   = [t[0] for t in turmas_alunos]
    dados_turma    = [t[1] for t in turmas_alunos]

    moradia        = stats_situacao_moradia()
    labels_moradia = [SITUACOES_MORADIA.get(m[0], m[0]) for m in moradia]
    dados_moradia  = [m[1] for m in moradia]

    vulneraveis_com_beneficio, vulneraveis_sem_beneficio = stats_vulnerabilidade_x_beneficio()

    return render(request, "painel.html", {
        "total_alunos":       stats_total_alunos(),
        "refeicoes_hoje":     stats_total_refeicoes_hoje(),
        "alunos_com_perfil":  stats_alunos_com_perfil(),
        "alunos_vulneraveis": stats_alunos_vulneraveis(),
        "labels_beneficios":  json.dumps(labels_ben),
        "dados_beneficios":   json.dumps(dados_ben_qtd),
        "dados_beneficios_valor": json.dumps(dados_ben_valor),
        "labels_turma":       json.dumps(labels_turma),
        "dados_turma":        json.dumps(dados_turma),
        "labels_moradia":     json.dumps(labels_moradia),
        "dados_moradia":      json.dumps(dados_moradia),
        "vulneraveis_com_beneficio": vulneraveis_com_beneficio,
        "vulneraveis_sem_beneficio": vulneraveis_sem_beneficio,
    })


# ======================================================
# RELATÓRIO PDF
# ======================================================

COR_MARCA        = colors.HexColor('#1D9E75')
COR_TEXTO_TITULO = colors.HexColor('#1D2B27')
COR_TEXTO_MUTED  = colors.HexColor('#6c757d')
COR_ZEBRA        = colors.HexColor('#f5f7f6')
COR_BORDA        = colors.HexColor('#e0e0e0')

LARGURA_CONTEUDO = 17 * cm  # A4 (21cm) - margens de 2cm de cada lado


def _cabecalho_pdf():
    """Faixa de topo com logo, nome da instituição e uma linha de destaque na cor da marca."""
    logo_path = os.path.join(settings.BASE_DIR, "static", "ifam_humaita_logo_inicio.png")
    s_titulo = ParagraphStyle('cab_titulo', fontName='Helvetica-Bold', fontSize=15,
                               leading=18, textColor=COR_TEXTO_TITULO)
    s_sub = ParagraphStyle('cab_sub', fontName='Helvetica', fontSize=10,
                            leading=13, textColor=COR_TEXTO_MUTED)

    try:
        logo = Image(logo_path, width=3.2 * cm, height=3.2 * cm * 120 / 418)
    except Exception:
        logo = Paragraph("", s_sub)

    textos = [
        Paragraph("IFAM Campus Humaitá", s_titulo),
        Paragraph("Assistência Estudantil — Sistema SocioEstudantil", s_sub),
    ]
    cabecalho = Table([[logo, textos]], colWidths=[3.5 * cm, LARGURA_CONTEUDO - 3.5 * cm])
    cabecalho.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    linha = Table([['']], colWidths=[LARGURA_CONTEUDO], rowHeights=[0.08 * cm])
    linha.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), COR_MARCA)]))

    return [cabecalho, Spacer(1, 0.35 * cm), linha, Spacer(1, 0.7 * cm)]


def _resumo_pdf(texto):
    """Caixa destacada na cor da marca para o total do relatório (substitui o antigo texto solto)."""
    p = Paragraph(texto, ParagraphStyle('resumo', fontName='Helvetica-Bold', fontSize=10,
                                         leading=13, textColor=colors.white))
    caixa = Table([[p]], colWidths=[LARGURA_CONTEUDO])
    caixa.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), COR_MARCA),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return caixa


def _sem_registros():
    p = Paragraph("Nenhum registro encontrado para este relatório.",
                   ParagraphStyle('vazio', fontName='Helvetica-Oblique', fontSize=10,
                                  textColor=COR_TEXTO_MUTED, alignment=TA_CENTER))
    caixa = Table([[p]], colWidths=[LARGURA_CONTEUDO], rowHeights=[1.4 * cm])
    caixa.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COR_ZEBRA),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
    ]))
    return caixa


def _estilo_tabela(alinhamentos=None):
    estilo = [
        ('BACKGROUND',     (0, 0), (-1, 0), COR_MARCA),
        ('TEXTCOLOR',      (0, 0), (-1, 0), colors.white),
        ('FONTNAME',       (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME',       (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',       (0, 0), (-1, -1), 8.5),
        ('LINEBELOW',      (0, 0), (-1, 0), 1, COR_MARCA),
        ('LINEBELOW',      (0, 1), (-1, -2), 0.4, COR_BORDA),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COR_ZEBRA]),
        ('ALIGN',          (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',     (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 6),
        ('LEFTPADDING',    (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 8),
    ]
    if alinhamentos:
        for col, alinhamento in enumerate(alinhamentos):
            estilo.append(('ALIGN', (col, 1), (col, -1), alinhamento))
    return TableStyle(estilo)


def _rodape_pdf(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(COR_MARCA)
    canvas.setLineWidth(0.7)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(COR_TEXTO_MUTED)
    canvas.drawString(2 * cm, 1.05 * cm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.drawRightString(A4[0] - 2 * cm, 1.05 * cm, f"Página {doc.page}")
    canvas.restoreState()


def relatorio_pdf(request):
    if request.method == "POST":
        tipo = request.POST.get("tipo_relatorio", "beneficios")

        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                   rightMargin=2*cm, leftMargin=2*cm,
                                   topMargin=1.8*cm, bottomMargin=2.2*cm)
        styles = getSampleStyleSheet()
        s_h2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=13,
                               leading=16, textColor=COR_TEXTO_TITULO, spaceAfter=2)
        s_nota = ParagraphStyle('nota', fontName='Helvetica-Oblique', fontSize=9,
                                 leading=12, textColor=COR_TEXTO_MUTED)

        elementos = _cabecalho_pdf()
        dados = [[]]
        alinhamentos = None

        if tipo == "beneficios":
            elementos.append(Paragraph("Relatório de Benefícios Ativos", s_h2))
            elementos.append(Spacer(1, 0.25*cm))
            registros = [r for r in listar_beneficios() if r[7] == 1]
            elementos.append(_resumo_pdf(f"Total: {len(registros)} benefícios ativos"))
            elementos.append(Spacer(1, 0.4*cm))
            dados = [["Nome", "Matrícula", "Tipo", "Valor (R$)", "Início", "Fim"]]
            for r in registros:
                dados.append([
                    r[1], r[2],
                    TIPOS_BENEFICIO.get(r[3], r[3]),
                    f"R$ {r[4]:.2f}",
                    r[5], r[6] or "Em aberto"
                ])
            alinhamentos = ['LEFT', 'LEFT', 'LEFT', 'RIGHT', 'CENTER', 'CENTER']

        elif tipo == "vulneraveis":
            elementos.append(Paragraph(
                "Relatório de Alunos em Situação de Vulnerabilidade", s_h2
            ))
            limite = SALARIO_MINIMO * LIMITE_VULNERABILIDADE
            elementos.append(Paragraph(
                f"Critério: renda per capita ≤ R$ {limite:.2f} "
                f"({LIMITE_VULNERABILIDADE}× salário mínimo — PNAES)",
                s_nota
            ))
            elementos.append(Spacer(1, 0.25*cm))
            registros = listar_alunos_vulneraveis()
            elementos.append(_resumo_pdf(f"Total: {len(registros)} alunos"))
            elementos.append(Spacer(1, 0.4*cm))
            dados = [["Nome", "Matrícula", "Turma", "Renda familiar", "Membros", "Renda p.c."]]
            for r in registros:
                dados.append([
                    r[0], r[1], r[2],
                    f"R$ {r[3]:.2f}", str(r[4]), f"R$ {r[5]:.2f}"
                ])
            alinhamentos = ['LEFT', 'LEFT', 'LEFT', 'RIGHT', 'CENTER', 'RIGHT']

        elif tipo == "alunos_turma":
            elementos.append(Paragraph("Relatório de Alunos por Turma", s_h2))
            elementos.append(Spacer(1, 0.25*cm))
            registros = stats_alunos_por_turma()
            elementos.append(_resumo_pdf(f"Total: {len(registros)} turmas"))
            elementos.append(Spacer(1, 0.4*cm))
            dados = [["Turma", "Alunos ativos"]]
            dados += [[r[0], str(r[1])] for r in registros]
            alinhamentos = ['LEFT', 'CENTER']

        elif tipo == "sem_perfil":
            elementos.append(Paragraph(
                "Relatório de Alunos sem Perfil Socioeconômico Cadastrado", s_h2
            ))
            elementos.append(Spacer(1, 0.25*cm))
            registros = listar_alunos_sem_perfil()
            elementos.append(_resumo_pdf(f"Total: {len(registros)} alunos"))
            elementos.append(Spacer(1, 0.4*cm))
            dados = [["Nome", "Matrícula", "Turma"]]
            dados += [list(r) for r in registros]
            alinhamentos = ['LEFT', 'LEFT', 'LEFT']

        elif tipo == "vulneraveis_sem_beneficio":
            elementos.append(Paragraph(
                "Relatório de Alunos Vulneráveis sem Benefício Ativo", s_h2
            ))
            elementos.append(Paragraph(
                "Alunos em situação de vulnerabilidade (critério PNAES) que ainda não "
                "recebem nenhum auxílio ativo — prioridade para atendimento.",
                s_nota
            ))
            elementos.append(Spacer(1, 0.25*cm))
            registros = listar_vulneraveis_sem_beneficio()
            elementos.append(_resumo_pdf(f"Total: {len(registros)} alunos"))
            elementos.append(Spacer(1, 0.4*cm))
            dados = [["Nome", "Matrícula", "Turma", "Renda p.c."]]
            for r in registros:
                dados.append([r[0], r[1], r[2], f"R$ {r[3]:.2f}"])
            alinhamentos = ['LEFT', 'LEFT', 'LEFT', 'RIGHT']

        if len(dados) > 1:
            tabela = Table(dados, repeatRows=1)
            tabela.setStyle(_estilo_tabela(alinhamentos))
            elementos.append(tabela)
        else:
            elementos.append(_sem_registros())

        doc.build(elementos, onFirstPage=_rodape_pdf, onLaterPages=_rodape_pdf)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="relatorio_{tipo}.pdf"'
        return response

    return render(request, "relatorio_pdf.html")