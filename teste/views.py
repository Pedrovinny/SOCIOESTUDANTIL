from django.shortcuts import render, redirect
from django.http import HttpResponse
from src.banco import *

import csv
import io
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


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


def leitor(request):
    mensagem = ""
    cor = "secondary"
    nome = ""
    if request.method == "POST":
        matricula = request.POST.get("matricula", "").strip()
        aluno = buscar_aluno_matricula(matricula)
        if aluno is None:
            mensagem = "Aluno não encontrado."
            cor = "danger"
        else:
            id_aluno = aluno[0]
            nome     = aluno[2]
            if aluno_ja_almocou_hoje(id_aluno):
                mensagem = "Aluno já retirou a refeição hoje."
                cor = "warning"
            else:
                registrar_refeicao(id_aluno)
                mensagem = "Pode retirar a refeição."
                cor = "success"
    return render(request, "leitor.html", {"mensagem": mensagem, "cor": cor, "nome": nome})


def relatorio(request):
    if request.method == "POST":
        data_inicial = request.POST["data_inicial"]
        data_final   = request.POST["data_final"]
        registros    = listar_refeicoes_periodo(data_inicial, data_final)
        response     = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="relatorio.csv"'
        writer = csv.writer(response)
        writer.writerow(["Matricula", "Nome", "Turma", "Data", "Hora"])
        for linha in registros:
            writer.writerow(linha)
        return response
    return render(request, "relatorio.html")


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
# PAINEL
# ======================================================

def painel(request):
    refeicoes_por_dia = stats_refeicoes_por_dia(30)
    labels_ref        = [r[0] for r in refeicoes_por_dia]
    dados_ref         = [r[1] for r in refeicoes_por_dia]

    beneficios_ativos = stats_beneficios_ativos()
    labels_ben        = [TIPOS_BENEFICIO.get(b[0], b[0]) for b in beneficios_ativos]
    dados_ben_qtd     = [b[1] for b in beneficios_ativos]

    return render(request, "painel.html", {
        "total_alunos":       stats_total_alunos(),
        "refeicoes_hoje":     stats_total_refeicoes_hoje(),
        "alunos_com_perfil":  stats_alunos_com_perfil(),
        "alunos_vulneraveis": stats_alunos_vulneraveis(),
        "labels_refeicoes":   json.dumps(labels_ref),
        "dados_refeicoes":    json.dumps(dados_ref),
        "labels_beneficios":  json.dumps(labels_ben),
        "dados_beneficios":   json.dumps(dados_ben_qtd),
    })


# ======================================================
# RELATÓRIO PDF
# ======================================================

def _estilo_tabela():
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#1D9E75')),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
        ('PADDING',       (0, 0), (-1, -1), 4),
    ])


def relatorio_pdf(request):
    if request.method == "POST":
        tipo         = request.POST.get("tipo_relatorio", "refeicoes")
        data_inicial = request.POST.get("data_inicial", "")
        data_final   = request.POST.get("data_final", "")

        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                   rightMargin=2*cm, leftMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        s_titulo = ParagraphStyle('titulo', parent=styles['Heading1'],
                                  alignment=TA_CENTER, fontSize=14)
        s_sub    = ParagraphStyle('sub', parent=styles['Normal'],
                                  alignment=TA_CENTER, fontSize=10)
        s_dir    = ParagraphStyle('dir', parent=styles['Normal'],
                                  alignment=TA_RIGHT, fontSize=9)

        elementos = [
            Paragraph("IFAM Campus Humaitá", s_titulo),
            Paragraph("Assistência Estudantil — Sistema Socioestudantil", s_sub),
            Spacer(1, 0.5*cm),
        ]

        if tipo == "refeicoes":
            elementos.append(Paragraph(
                f"Relatório de Refeições: {data_inicial} a {data_final}",
                styles['Heading2']
            ))
            elementos.append(Spacer(1, 0.3*cm))
            registros = listar_refeicoes_periodo(data_inicial, data_final)
            elementos.append(Paragraph(f"Total: {len(registros)} refeições", styles['Normal']))
            elementos.append(Spacer(1, 0.2*cm))
            dados = [["Matrícula", "Nome", "Turma", "Data", "Hora"]]
            dados += [list(r) for r in registros]

        elif tipo == "beneficios":
            elementos.append(Paragraph("Relatório de Benefícios Ativos", styles['Heading2']))
            elementos.append(Spacer(1, 0.3*cm))
            registros = [r for r in listar_beneficios() if r[7] == 1]
            elementos.append(Paragraph(f"Total: {len(registros)} benefícios ativos", styles['Normal']))
            elementos.append(Spacer(1, 0.2*cm))
            dados = [["Nome", "Matrícula", "Tipo", "Valor (R$)", "Início", "Fim"]]
            for r in registros:
                dados.append([
                    r[1], r[2],
                    TIPOS_BENEFICIO.get(r[3], r[3]),
                    f"R$ {r[4]:.2f}",
                    r[5], r[6] or "Em aberto"
                ])

        elif tipo == "vulneraveis":
            elementos.append(Paragraph(
                "Relatório de Alunos em Situação de Vulnerabilidade",
                styles['Heading2']
            ))
            elementos.append(Spacer(1, 0.3*cm))
            registros = listar_alunos_vulneraveis()
            limite    = SALARIO_MINIMO * LIMITE_VULNERABILIDADE
            elementos.append(Paragraph(
                f"Critério: renda per capita ≤ R$ {limite:.2f} "
                f"({LIMITE_VULNERABILIDADE}× salário mínimo — PNAES)",
                styles['Normal']
            ))
            elementos.append(Paragraph(f"Total: {len(registros)} alunos", styles['Normal']))
            elementos.append(Spacer(1, 0.2*cm))
            dados = [["Nome", "Matrícula", "Turma", "Renda familiar", "Membros", "Renda p.c."]]
            for r in registros:
                dados.append([
                    r[0], r[1], r[2],
                    f"R$ {r[3]:.2f}", str(r[4]), f"R$ {r[5]:.2f}"
                ])

        if len(dados) > 1:
            tabela = Table(dados, repeatRows=1)
            tabela.setStyle(_estilo_tabela())
            elementos.append(tabela)

        elementos.append(Spacer(1, 0.5*cm))
        elementos.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            s_dir
        ))

        doc.build(elementos)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="relatorio_{tipo}.pdf"'
        return response

    return render(request, "relatorio_pdf.html")