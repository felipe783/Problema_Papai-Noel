#!/usr/bin/env python3
"""gerar_slides.py — monta slides.pptx (v2) a partir dos CSVs, PNGs e do código real.

v3: revisão de design pela skill pptx (títulos 36 pt, corpo >= 14 pt, sem faixas
decorativas), estados de Noel, correta × ingênua em linha do tempo e perguntas
prováveis nas notas. v2: amplia a v1 (backup/slides_v1.pptx) com fundamentos, os mecanismos de
sincronização linha a linha, cenários de execução, propriedades, método e um
apêndice de respostas rápidas. Os números vêm de dados/; as linhas citadas
foram conferidas em src/. Notas do apresentador divididas entre
[Integrante 1], [Integrante 2] e [Integrante 3]; slides marcados "APOIO" são
para perguntas e podem ser pulados numa fala de 8 minutos.
Uso: python3 scripts/gerar_slides.py   (requer python-pptx e pandas)
"""
import re
import textwrap
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parent.parent
D, G, SRC = RAIZ / "dados", RAIZ / "graficos", RAIZ / "src"

VERDE = RGBColor(0x1F, 0x4D, 0x3A)      # dominante
VERDE_CLARO = RGBColor(0xE6, 0xEF, 0xEA)
VERMELHO = RGBColor(0xB3, 0x1B, 0x2B)   # acento
LARANJA = RGBColor(0xEB, 0x68, 0x34)    # = preparação nos gráficos
AZUL = RGBColor(0x2A, 0x78, 0xD6)       # = ajuda nos gráficos
CINZA_BARRA = RGBColor(0xC9, 0xC8, 0xC3)
TINTA = RGBColor(0x1A, 0x1A, 0x1A)
CINZA = RGBColor(0x55, 0x55, 0x55)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)
FUNDO_COD = RGBColor(0x1E, 0x1E, 0x1E)
COD_TXT = RGBColor(0xE8, 0xE8, 0xE8)
COD_NUM = RGBColor(0x8A, 0x8A, 0x8A)
COD_DEST = RGBColor(0xF2, 0xC9, 0x4C)
COD_OK = RGBColor(0x8F, 0xE3, 0xA8)
CINZA_CLARO = RGBColor(0xF3, 0xF4, 0xF6)
FONTE_T, FONTE_C, FONTE_M = "Cambria", "Calibri", "Courier New"


def br(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


# ------------------------------------------------------------------ dados reais
res = pd.read_csv(D / "resumo.csv")
tab = pd.read_csv(D / "tabela_esperas.csv").set_index("configuracao").to_dict("index")
eventos = pd.read_csv(D / "eventos.csv")
n_exec, n_ok = len(res), int((res["status"] == "ok").sum())
viol = int(res["violacoes_prioridade"].sum() + res["violacoes_regras"].sum())
est = pd.read_csv(D / "estresse" / "resumo.csv")
piloto = pd.read_csv(D / "piloto" / "resumo.csv")
tt = pd.read_csv(D / "piloto" / "teste_timeout" / "resumo.csv").iloc[0]
ing = pd.read_csv(D / "ingenua" / "resumo.csv").iloc[0]
ing_ev = pd.read_csv(D / "ingenua" / "eventos.csv")
tp = pd.read_csv(D / "teste_prioridade" / "resumo.csv").iloc[0]
saida_teste = (D / "teste_prioridade" / "saida.txt").read_text().strip().splitlines()
r03, r06, r12, a05, d30 = (tab[k] for k in ("E03_R10", "E06_R10", "E12_R10", "E06_R05", "E06_R30"))
esp = pd.read_csv(D / "espera_elfos.csv")
_g3 = esp[esp["execucao"].str.startswith("E06_R10")].groupby(["execucao", "grupo_id"])["espera_ms"].max().unstack()
g3 = {g: (_g3[g].mean(), _g3[g].min(), _g3[g].max()) for g in _g3.columns}
FONTE_COD = {f: (SRC / f).read_text().splitlines() for f in ("main.c", "noel.c", "elfo.c", "rena.c")}


def linha(arq, n):
    """Texto real da linha n (base 1) de src/arq — o slide nunca digita código à mão."""
    return FONTE_COD[arq][n - 1]


def t_ev(df, ev, g=None):
    q = df[df["evento"] == ev]
    if g is not None:
        q = q[q["grupo_id"] == g]
    return float(q["t_ms"].iloc[0])


def faixas(execucao, df=None):
    """Intervalos de preparação/ajuda e marcas de uma execução, lidos de eventos.csv."""
    ev = eventos if df is None else df
    ev = ev[ev["execucao"] == execucao]
    par = lambda a, b: list(zip(ev[ev["evento"] == a]["t_ms"], ev[ev["evento"] == b]["t_ms"],
                                ev[ev["evento"] == a]["grupo_id"]))
    return {"prep": par("inicio_preparacao", "fim_preparacao"), "ajuda": par("inicio_ajuda", "fim_ajuda"),
            "prontos": list(zip(ev[ev["evento"] == "grupo_pronto"]["t_ms"], ev[ev["evento"] == "grupo_pronto"]["grupo_id"])),
            "nona": t_ev(ev, "nona_rena"), "fim": t_ev(ev, "encerramento")}


ing_dec = ing_ev[ing_ev["evento"] == "decisao"]["t_ms"].tolist()

# ------------------------------------------------------------------ helpers
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
LAYOUT = prs.slide_layouts[6]
NUM = [0]


def novo(fundo=BRANCO):
    s = prs.slides.add_slide(LAYOUT)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = fundo
    NUM[0] += 1
    return s


def texto(s, x, y, w, h, linhas, tam=16, cor=TINTA, fonte=FONTE_C, negrito=False, alinh=PP_ALIGN.LEFT,
          ancora=MSO_ANCHOR.TOP, nome=None, espaco=4, margem=0.05):
    """linhas: str ou lista de str / (str, dict) com opções por parágrafo; dict pode ter 'runs'."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if nome:
        tb.name = nome
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = ancora
    tf.margin_left = tf.margin_right = Inches(margem)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    if isinstance(linhas, str):
        linhas = [linhas]
    for i, l in enumerate(linhas):
        op = {}
        if isinstance(l, tuple):
            l, op = l
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = op.get("alinh", alinh)
        p.space_after = Pt(op.get("espaco", espaco))
        runs = op.get("runs") or [(("•  " if op.get("bala") else "") + l, {})]
        if op.get("bala") and op.get("runs"):
            runs = [("•  ", {})] + runs
        for txt, rop in runs:
            r = p.add_run()
            r.text = txt
            f = r.font
            f.size = Pt(rop.get("tam", op.get("tam", tam)))
            f.bold = rop.get("negrito", op.get("negrito", negrito))
            f.italic = rop.get("italico", op.get("italico", False))
            f.name = rop.get("fonte", op.get("fonte", fonte))
            f.color.rgb = rop.get("cor", op.get("cor", cor))
    return tb


def titulo(s, txt, cor=VERDE, apoio=False):
    texto(s, 0.6, 0.35, 11.4 if apoio else 12.1, 0.9, txt, tam=36, cor=cor, fonte=FONTE_T, negrito=True,
          nome="Título")
    if apoio:
        c = caixa(s, 12.0, 0.5, 0.85, 0.36, cor=CINZA_BARRA)
        rotulo(c, "APOIO", 11, TINTA)


def caixa(s, x, y, w, h, cor=VERDE_CLARO, borda=None, forma=MSO_SHAPE.ROUNDED_RECTANGLE, raio=0.08):
    sh = s.shapes.add_shape(forma, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = cor
    if borda is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = borda
        sh.line.width = Pt(1.25)
    sh.shadow.inherit = False
    if forma == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = raio
    return sh


def rotulo(sh, txt, tam=14, cor=BRANCO, negrito=True, alinh=PP_ALIGN.CENTER, fonte=FONTE_C):
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.06)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, l in enumerate(txt.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alinh
        r = p.add_run()
        r.text = l
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(tam), negrito, cor, fonte
    return sh


def circulo(s, x, y, d, txt, cor=VERDE, tam=20):
    return rotulo(caixa(s, x, y, d, d, cor=cor, forma=MSO_SHAPE.OVAL), txt, tam)


def seta(s, x1, y1, x2, y2, cor=CINZA, larg=1.75):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = cor
    c.line.width = Pt(larg)
    ln = c.line._get_or_add_ln()
    ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return c


def linha_reta(s, x1, y1, x2, y2, cor=CINZA, larg=1.0, tracejada=False):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = cor
    c.line.width = Pt(larg)
    if tracejada:
        ln = c.line._get_or_add_ln()
        ln.append(ln.makeelement(qn("a:prstDash"), {"val": "dash"}))
    return c


def codigo(s, x, y, w, h, arq, linhas_num, destaque=(), tam=13, titulo_cod=None, comentarios=None):
    """Caixa escura com linhas REAIS de src/arq (lidas do arquivo), numeradas; destaque em amarelo."""
    caixa(s, x, y, w, h, cor=FUNDO_COD, raio=0.04)
    comentarios = comentarios or {}
    sem_coment = lambda t: re.sub(r"\s*/\*.*?\*/", "", t).rstrip()  # comentários ficam no arquivo, não no slide
    reais = [sem_coment(linha(arq, n)) for n in linhas_num if n is not None]
    recuo = min(len(l) - len(l.lstrip()) for l in reais if l.strip())
    maior = max(len(l) - recuo for l in reais) + 4
    tam = max(12, min(tam, int((w - 0.3) * 72 / (0.6 * maior))))  # Courier: largura ≈ 0,6 × corpo
    lin = []
    if titulo_cod:
        lin.append((titulo_cod, {"cor": COD_NUM, "tam": tam - 1, "espaco": 3}))
    for n in linhas_num:
        if n is None:
            lin.append(("   ⋮", {"cor": COD_NUM, "espaco": 0}))
            continue
        txt = sem_coment(linha(arq, n))[recuo:]
        cor = COD_DEST if n in destaque else COD_TXT
        runs = [(f"{n:>3} ", {"cor": COD_NUM}), (txt, {"cor": cor, "negrito": n in destaque})]
        if n in comentarios:
            runs.append((f"  ← {comentarios[n]}", {"cor": COD_OK, "fonte": FONTE_C, "negrito": True}))
        lin.append(("", {"runs": runs, "espaco": 0}))
    texto(s, x + 0.12, y + 0.1, w - 0.24, h - 0.2, lin, tam=tam, fonte=FONTE_M, cor=COD_TXT, espaco=0)


def tabela(s, linhas, x, y, larguras, alt_linha=0.42, tam=14, cab_cor=VERDE, destaque=None):
    """linhas[0] = cabeçalho. Célula pode ser str ou (str, {cor, negrito})."""
    tb = s.shapes.add_table(len(linhas), len(larguras), Inches(x), Inches(y), Inches(sum(larguras)),
                            Inches(alt_linha * len(linhas))).table
    for j, w in enumerate(larguras):
        tb.columns[j].width = Inches(w)
    for i, l in enumerate(linhas):
        tb.rows[i].height = Inches(alt_linha)
        for j, v in enumerate(l):
            op = {}
            if isinstance(v, tuple):
                v, op = v
            c = tb.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.text = v
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    f = r.font
                    f.size, f.name = Pt(op.get("tam", tam)), op.get("fonte", FONTE_C)
                    f.bold = i == 0 or op.get("negrito", False)
                    f.color.rgb = BRANCO if i == 0 else op.get("cor", TINTA)
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = cab_cor
            elif destaque and i in destaque:
                c.fill.fore_color.rgb = RGBColor(0xFB, 0xEC, 0xEC)
            else:
                c.fill.fore_color.rgb = BRANCO if i % 2 else VERDE_CLARO
    return tb


def imagem(s, arq, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return s.shapes.add_picture(str(arq), Inches(x), Inches(y), **kw)


def notas(s, txt):
    s.notes_slide.notes_text_frame.text = txt


def rodape(s, escuro=False):
    cor = BRANCO if escuro else CINZA
    texto(s, 0.6, 7.02, 9, 0.35, "Tema 11 — Problema do Papai Noel · Sistemas Operacionais (FAG)", tam=10, cor=cor)
    texto(s, 11.9, 7.02, 0.8, 0.35, str(NUM[0]), tam=10, cor=cor, alinh=PP_ALIGN.RIGHT)


def divisor(nome, sub, n):
    s = novo(VERDE)
    circulo(s, 0.9, 2.75, 1.2, str(n), cor=VERMELHO, tam=36)
    texto(s, 2.4, 2.65, 10, 0.9, nome, tam=40, cor=BRANCO, fonte=FONTE_T, negrito=True)
    texto(s, 2.4, 3.55, 10, 0.8, sub, tam=20, cor=BRANCO)
    rodape(s, escuro=True)
    return s


def linha_do_tempo(s, x, y, w, t0, t1, fx, rotulo_txt, alt=0.42, marcas=True):
    """Faixa do estado de Noel (dados reais) entre t0 e t1 ms."""
    esc = lambda t: x + (min(max(t, t0), t1) - t0) / (t1 - t0) * w
    texto(s, x - 1.75, y - 0.02, 1.65, alt + 0.04, rotulo_txt, tam=14, negrito=True, alinh=PP_ALIGN.RIGHT,
          ancora=MSO_ANCHOR.MIDDLE)
    caixa(s, x, y, w, alt, cor=CINZA_BARRA, forma=MSO_SHAPE.RECTANGLE)
    for a, b, _ in fx["prep"]:
        rotulo(caixa(s, esc(a), y, esc(b) - esc(a), alt, cor=LARANJA, forma=MSO_SHAPE.RECTANGLE), "viagem", 12)
    for a, b, g in fx["ajuda"]:
        rotulo(caixa(s, esc(a), y, esc(b) - esc(a), alt, cor=AZUL, forma=MSO_SHAPE.RECTANGLE), f"g{int(g)}", 12)
    if marcas:
        for t, g in fx["prontos"]:
            linha_reta(s, esc(t), y - 0.12, esc(t), y + alt + 0.12, cor=RGBColor(0x1B, 0xAF, 0x7A), larg=2,
                       tracejada=True)
        linha_reta(s, esc(fx["nona"]), y - 0.12, esc(fx["nona"]), y + alt + 0.12,
                   cor=RGBColor(0x62, 0x50, 0xD6), larg=2.5)
    return esc


# ================================================================== 1. capa
s = novo(VERDE)
texto(s, 0.9, 1.7, 11.5, 1.6, "Problema do Papai Noel", tam=54, cor=BRANCO, fonte=FONTE_T, negrito=True)
texto(s, 0.9, 2.9, 11.5, 0.9, "Sincronização com pthreads: implementação, experimentos e análise", tam=24,
      cor=BRANCO)
texto(s, 0.9, 4.5, 11.5, 1.4, ["Tema 11 · Sistemas Operacionais · Prof. Lucca Abbado Neres · FAG",
                               "[Integrante 1] · [Integrante 2] · [Integrante 3]"], tam=18, cor=BRANCO, espaco=8)
for i, (n, rot) in enumerate([("1", "Noel"), ("9", "renas"), ("N", "elfos")]):
    circulo(s, 9.4 + i * 1.15, 5.75, 0.95, n, cor=VERMELHO, tam=24)
    texto(s, 9.3 + i * 1.15, 6.72, 1.15, 0.35, rot, tam=12, cor=BRANCO, alinh=PP_ALIGN.CENTER)
notas(s, "[Integrante 1] (~10 s) Apresentar o grupo e o tema. Implementamos em C com pthreads, rodamos "
         "25 execuções e vamos mostrar a lógica, a sincronização no código, a demonstração e os resultados. "
         "Slides marcados APOIO são para responder perguntas; numa fala de 8 minutos podem ser pulados.")

# ================================================================== 2. roteiro
s = novo()
titulo(s, "Roteiro")
etapas = [("Fundamentos", "corrida, seção crítica,\nmutex × semáforo"),
          ("O problema", "elfos em trios,\n9 renas, prioridade"),
          ("Solução", "mecanismos, valores\niniciais, linhas reais"),
          ("Propriedades", "deadlock, starvation,\nprincípios"),
          ("Resultados", "método, G1–G4,\nlimitações")]
for i, (t, sub) in enumerate(etapas):
    x = 0.75 + i * 2.5
    circulo(s, x + 0.55, 2.0, 1.0, str(i + 1), cor=VERMELHO if i == 2 else VERDE, tam=26)
    if i < 4:
        seta(s, x + 1.65, 2.5, x + 2.95, 2.5)
    texto(s, x - 0.1, 3.2, 2.3, 0.5, t, tam=20, negrito=True, alinh=PP_ALIGN.CENTER, cor=VERDE)
    texto(s, x - 0.1, 3.75, 2.3, 1.0, sub, tam=15, alinh=PP_ALIGN.CENTER, cor=CINZA)
caixa(s, 0.6, 5.2, 12.15, 1.3)
texto(s, 0.85, 5.3, 11.7, 1.1, [
    ("", {"runs": [("Mensagem central: ", {"negrito": True, "cor": VERDE}),
                   ("1 mutex protege todo o estado; 4 variáveis de condição fazem as threads esperarem sem gastar CPU; "
                    "só Noel decide, e decide com o mutex — renas primeiro, sem interromper a ajuda.", {})]}),
], tam=18, ancora=MSO_ANCHOR.MIDDLE)
rodape(s)
notas(s, "[Integrante 1] (~15 s) Vamos dos fundamentos até os resultados. O ponto 3, solução, é o centro: "
         "é onde mostramos como o mutex e as variáveis de condição aparecem no código, com as linhas reais.")

# ================================================================== FUNDAMENTOS
divisor("Fundamentos", "O que é um problema de sincronização e por que o SO está no meio dele", 1)
notas(prs.slides[-1], "[Integrante 1] Transição: primeiro os conceitos que o professor vai cobrar.")

# ------------------------------------------------------------------ 4. sincronização e SO
s = novo()
titulo(s, "Sincronização: quando a ordem importa")
cards = [("Concorrência", "várias threads progridem ao mesmo tempo; quem roda e quando é decidido pelo escalonador do SO"),
         ("Processo × thread", "processo = espaço de memória próprio; threads do mesmo processo compartilham a memória — aqui, a struct Oficina"),
         ("Seção crítica", "trecho que lê/altera dados compartilhados e não pode ser executado por duas threads ao mesmo tempo"),
         ("Condição de corrida", "o resultado depende do entrelaçamento das instruções; uma thread apaga o trabalho da outra")]
for i, (t, d) in enumerate(cards):
    x, y = 0.6 + (i % 2) * 3.95, 1.5 + (i // 2) * 2.65
    caixa(s, x, y, 3.75, 2.45)
    texto(s, x + 0.2, y + 0.12, 3.4, 0.5, t, tam=19, negrito=True, cor=VERDE)
    texto(s, x + 0.2, y + 0.65, 3.4, 1.75, d, tam=15)
caixa(s, 8.65, 1.5, 4.1, 5.1, cor=VERDE)
texto(s, 8.9, 1.65, 3.7, 0.5, "Onde entra o SO", tam=20, negrito=True, cor=BRANCO)
texto(s, 8.9, 2.25, 3.7, 4.3, [
    ("Cria e escalona as threads: a ordem não é controlada pelo programa", {"bala": True}),
    ("Bloqueia e acorda threads: quem espera um mutex ou uma condição sai da CPU", {"bala": True}),
    ("Fornece as primitivas (pthreads, relógio monotônico, timers)", {"bala": True}),
    ("Um programa concorrente só é correto se for correto para TODA ordem possível", {"bala": True, "negrito": True}),
], tam=15, cor=BRANCO, espaco=10)
rodape(s)
notas(s, "[Integrante 1] (~40 s) Problema de sincronização: threads compartilham dados e a correção depende "
         "da ordem em que executam. Quem decide a ordem é o escalonador do SO, não nós. Por isso precisamos "
         "de exclusão mútua para a seção crítica e de uma forma de esperar eventos sem gastar CPU — e é o SO "
         "que tira a thread da CPU quando ela bloqueia e a acorda depois. Nossas threads são do mesmo "
         "processo, então compartilham a memória: tudo fica numa struct chamada Oficina.")

# ------------------------------------------------------------------ 5. corrida real
s = novo()
titulo(s, "Condição de corrida: duas renas, um contador")
linhas = [["Passo", "Rena A", "Rena B", "renas_prontas"],
          ["1", "lê 7", "", "7"], ["2", "", "lê 7", "7"], ["3", "soma e grava 8", "", "8"],
          ["4", "", ("soma e grava 8", {"cor": VERMELHO, "negrito": True}), ("8  ✗", {"cor": VERMELHO, "negrito": True})]]
tabela(s, linhas, 0.6, 1.55, [1.0, 2.2, 2.2, 1.9], alt_linha=0.55, tam=16)
texto(s, 0.6, 4.45, 7.3, 1.2, [
    ("", {"runs": [("Sem proteção: ", {"negrito": True, "cor": VERMELHO}),
                   ("renas_prontas++ é ler → somar → gravar. Com 9 renas o contador pode ficar em 8: "
                    "Noel nunca prepara a viagem e o episódio termina em timeout.", {})]}),
], tam=16)
codigo(s, 8.2, 1.55, 4.55, 2.55, "rena.c", [23, None, 28, None, 30], destaque=(23, 28),
       titulo_cod="rena.c — thread_rena()", tam=13)
texto(s, 8.2, 4.25, 4.55, 2.4, [
    ("Com o mutex (rena.c:23)", {"negrito": True, "cor": VERDE, "tam": 17}),
    ("A rena B fica bloqueada no pthread_mutex_lock até A soltar", {"bala": True}),
    ("Ler-somar-gravar vira indivisível para as outras threads", {"bala": True}),
    ("Quem ganha a disputa não é FIFO: o SO escolhe", {"bala": True}),
], tam=15, espaco=6)
rodape(s)
notas(s, "[Integrante 1] (~40 s) Exemplo concreto do nosso código. renas_prontas++ parece uma operação, mas "
         "são três. Se duas renas leem 7 ao mesmo tempo, as duas gravam 8 e uma chegada se perde: o contador "
         "nunca chega a 9. No código, a rena trava o mutex na linha 23 de rena.c antes de incrementar na "
         "linha 28; a segunda rena bloqueia no lock até a primeira soltar.")

# ------------------------------------------------------------------ 6. if + contador
s = novo()
titulo(s, "Por que um if e um contador não bastam")
caixa(s, 0.6, 1.5, 5.95, 4.0, cor=RGBColor(0xFB, 0xEC, 0xEC))
texto(s, 0.85, 1.62, 5.5, 0.5, "Sem mutex: o 4º elfo invade", tam=19, negrito=True, cor=VERMELHO)
passos = [("Elfo 2", "testa n < 3  (n = 2)  ✓"), ("Elfo 3", "testa n < 3  (n = 2)  ✓"),
          ("Elfo 2", "grava membros[2]; n = 3"), ("Elfo 3", "grava membros[2]; n = 4  ✗")]
for i, (q, a) in enumerate(passos):
    y = 2.3 + i * 0.74
    rotulo(caixa(s, 0.85, y, 1.25, 0.56, cor=VERDE if q == "Elfo 2" else VERMELHO), q, 15)
    texto(s, 2.25, y, 4.2, 0.56, a, tam=16, ancora=MSO_ANCHOR.MIDDLE, fonte=FONTE_M)
caixa(s, 6.8, 1.5, 5.95, 4.0)
texto(s, 7.05, 1.62, 5.5, 0.5, "Com mutex: testar e agir é indivisível", tam=19, negrito=True, cor=VERDE)
texto(s, 7.05, 2.25, 5.5, 3.2, [
    ("elfo.c:27 trava; o elfo lê grupo_aberto, inscreve-se, e o 3º fecha o grupo (PRONTO) e avança grupo_aberto", {"bala": True}),
    ("Só depois solta o mutex (wait em elfo.c:58)", {"bala": True}),
    ("O 4º elfo, ao entrar, já vê grupo_aberto = próximo grupo: não existe instante em que ele veja o grupo cheio e ainda aberto", {"bala": True}),
], tam=16, espaco=8)
texto(s, 0.6, 5.75, 12.15, 1.0, [
    ("", {"runs": [("E uma flag caseira?  ", {"negrito": True, "cor": VERDE}),
                   ("while (ocupado); ocupado = 1;  ", {"fonte": FONTE_M}),
                   ("sofre a mesma corrida entre o teste e a atribuição — e ainda é espera ocupada. "
                    "Só uma instrução atômica do hardware, usada por dentro do mutex, resolve.", {})]}),
], tam=16)
rodape(s)
notas(s, "[Integrante 1] (~40 s) Pergunta clássica: por que não basta um if com contador? Porque testar e agir "
         "são dois passos. Dois elfos podem ver n igual a 2, os dois passam no if e os dois escrevem na mesma "
         "posição: um quarto elfo invade o grupo. No nosso código o if existe, mas está dentro do mutex — "
         "teste, inscrição e fechamento do grupo acontecem sem soltar o lock. Uma flag feita à mão tem o "
         "mesmo problema e ainda gasta CPU.")

# ------------------------------------------------------------------ 7. mutex × semáforo × cond
s = novo()
titulo(s, "Mutex, semáforo e variável de condição")
linhas = [["", "Mutex", "Semáforo", "Variável de condição"],
          ["Para quê", "exclusão mútua", "contar recursos / avisos", "esperar uma condição"],
          ["Estado inicial", "destravado (sem valor numérico)", "um número: sem_init(&s, 0, valor)", "fila vazia (sem valor)"],
          ["Tem dono?", "sim: só quem travou destrava", "não: qualquer thread dá post", "não; sempre usada com um mutex"],
          ["Guarda avisos?", "—", "sim, no contador", "não: signal sem ninguém esperando se perde"],
          ["Operações", "lock / unlock", "wait (−1, bloqueia em 0) / post (+1)", "wait / signal / broadcast"],
          ["Neste projeto", ("1: mutex", {"negrito": True, "cor": VERDE}), ("nenhum", {"negrito": True, "cor": VERMELHO}),
           ("4: cv_largada, cv_noel, cv_elfos, cv_renas", {"negrito": True, "cor": VERDE})]]
tabela(s, linhas, 0.6, 1.5, [2.2, 3.15, 3.4, 3.4], alt_linha=0.6, tam=15)
texto(s, 0.6, 5.95, 12.15, 0.8, [
    ("", {"runs": [("Por que cond var e não semáforo? ", {"negrito": True, "cor": VERDE}),
                   ("Noel espera um predicado composto (9 renas OU grupo pronto) e decide olhando as duas demandas "
                    "na mesma seção crítica. grep \"sem_\" em src/ → nada.", {})]}),
], tam=16)
rodape(s)
notas(s, "[Integrante 2] (~45 s) Mutex é um cadeado com dono, para exclusão mútua. Semáforo é um contador: "
         "wait decrementa e bloqueia em zero, post incrementa; ele lembra os avisos e não tem dono. Variável de "
         "condição é uma fila de espera sem memória, sempre usada com um mutex e um predicado. Nossa "
         "implementação usa um mutex e quatro variáveis de condição — nenhum semáforo. Escolhemos cond var "
         "porque Noel precisa esperar 'nove renas ou um grupo' e decidir olhando as duas coisas juntas.")

# ================================================================== O PROBLEMA
divisor("O problema", "Elfos em grupos de três, nove renas e uma única decisão por vez", 2)
notas(prs.slides[-1], "[Integrante 1] Transição para o problema.")

# ------------------------------------------------------------------ 9. problema (v1)
s = novo()
titulo(s, "O problema: duas demandas, um único Noel")
caixa(s, 0.6, 1.5, 5.9, 4.4)
circulo(s, 0.95, 1.85, 0.9, "3", tam=26)
texto(s, 2.05, 1.9, 4.3, 0.9, "Grupos de exatamente 3 elfos", tam=20, negrito=True, ancora=MSO_ANCHOR.MIDDLE)
texto(s, 0.95, 3.0, 5.3, 2.9, [
    ("Cada elfo faz um pedido (versão finita)", {"bala": True}),
    ("O elfo i chega em 10 + i ms", {"bala": True}),
    ("Ajudar um grupo dura 3 ms e não pode ser interrompido", {"bala": True}),
    ("Nenhum elfo pode invadir um grupo fechado ou em atendimento", {"bala": True}),
], tam=18, espaco=10)
caixa(s, 6.85, 1.5, 5.9, 4.4)
circulo(s, 7.2, 1.85, 0.9, "9", cor=VERMELHO, tam=26)
texto(s, 8.3, 1.9, 4.3, 0.9, "Nove renas, uma viagem", tam=20, negrito=True, ancora=MSO_ANCHOR.MIDDLE)
texto(s, 7.2, 3.0, 5.3, 2.9, [
    ("Chegam juntas: antes (5 ms), junto (10 ms) ou depois (30 ms)", {"bala": True}),
    ("A viagem só é preparada com as 9 renas (5 ms)", {"bala": True}),
    ("Prioridade: com as duas demandas prontas, Noel escolhe as renas", {"bala": True}),
    ("O programa encerra quando a viagem e todos os grupos terminam", {"bala": True}),
], tam=18, espaco=10)
texto(s, 0.6, 6.1, 12.15, 0.6, "Noel é um recurso único e disputado — como uma CPU com clientes de prioridades diferentes, "
      "que só decide entre tarefas (não preemptivo).", tam=16, cor=CINZA)
rodape(s)
notas(s, "[Integrante 1] (~45 s) Noel dorme até ser acordado. Elfos só são atendidos em grupos de três, e um "
         "quarto elfo não pode entrar num grupo já formado. As nove renas precisam estar todas presentes para a "
         "viagem. Se as duas demandas estiverem prontas, a regra manda escolher as renas. Relação com o SO: "
         "Noel é como uma CPU disputada por clientes com prioridades diferentes, e ele não interrompe uma "
         "tarefa em andamento — é um escalonador não preemptivo.")

# ================================================================== SOLUÇÃO
divisor("Solução e sincronização", "Threads, mecanismos, valores iniciais e as linhas reais do código", 3)
notas(prs.slides[-1], "[Integrante 2] Transição: agora a parte central, a sincronização.")

# ------------------------------------------------------------------ 11. arquitetura (v1 revisado)
s = novo()
titulo(s, "Arquitetura: 1 + 9 + N threads, um estado")
blocos = [("Noel", "1 thread · noel.c", "dorme em cv_noel; decide com o mutex: renas primeiro; só ele altera o estado dos grupos e da viagem", VERMELHO),
          ("Renas", "9 threads · rena.c", "contam-se em renas_prontas; a 9ª acorda Noel; esperam em cv_renas", VERDE),
          ("Elfos", "N threads · elfo.c", "entram no grupo aberto; o 3º fecha o grupo e acorda Noel; esperam em cv_elfos", VERDE)]
for i, (nome, qtd, desc, cor) in enumerate(blocos):
    x = 0.6 + i * 4.1
    caixa(s, x, 1.5, 3.8, 2.35)
    texto(s, x + 0.25, 1.62, 3.4, 0.5, nome, tam=22, negrito=True, cor=cor)
    texto(s, x + 0.25, 2.1, 3.4, 0.4, qtd, tam=14, cor=CINZA)
    texto(s, x + 0.25, 2.5, 3.4, 1.35, desc, tam=15)
    seta(s, x + 1.9, 3.9, x + 1.9, 4.35, cor=VERDE, larg=2)
caixa(s, 0.6, 4.4, 12.15, 2.3, cor=VERDE)
texto(s, 0.85, 4.5, 11.7, 0.5, "Oficina o  (main.c:171) — \"todos os campos são protegidos por mutex\" (comum.h:78)",
      tam=18, negrito=True, cor=BRANCO)
campos = ["renas_prontas", "grupos[k] {n, estado}", "grupo_aberto", "grupos_fechados", "proximo_grupo",
          "viagem_iniciada / _concluida", "abortar", "largada"]
for i, c in enumerate(campos):
    x, y = 0.85 + (i % 4) * 2.95, 5.15 + (i // 4) * 0.7
    rotulo(caixa(s, x, y, 2.8, 0.55, cor=BRANCO), c, 14, VERDE, fonte=FONTE_M)
rodape(s)
notas(s, "[Integrante 2] (~30 s) São 1 thread Noel, 9 renas e N elfos, todas criadas antes do primeiro join. "
         "Todas recebem um ponteiro para a mesma struct, a Oficina, que guarda todo o estado compartilhado: "
         "contador de renas, grupos, índices da fila de grupos, flags da viagem. A regra do projeto está "
         "escrita no código: todo campo dessa struct só é lido ou alterado com o mutex.")

# ------------------------------------------------------------------ 12. mecanismos
s = novo()
titulo(s, "Os 5 mecanismos: onde nascem, quem usa")
linhas = [["Mecanismo", "Declarado", "Inicializado", "Quem espera", "Quem libera / avisa"],
          [("mutex", {"negrito": True}), "comum.h:82", ("main.c:131", {"negrito": True, "cor": VERMELHO}), "qualquer thread no lock", "a dona, no unlock"],
          ["cv_largada", "comum.h:83", "main.c:132", "threads (main.c:30) e main (main.c:209)", "threads (main.c:28) e main (main.c:212)"],
          ["cv_noel", "comum.h:84", "main.c:136-140", "Noel (noel.c:101)", "9ª rena (rena.c:33), 3º elfo (elfo.c:53)"],
          ["cv_elfos", "comum.h:85", "main.c:133", "elfos (elfo.c:58)", "Noel (noel.c:73, 143)"],
          ["cv_renas", "comum.h:86", "main.c:134", "renas (rena.c:37)", "Noel (noel.c:41, 144)"]]
tabela(s, linhas, 0.6, 1.5, [1.75, 1.6, 1.9, 3.35, 3.55], alt_linha=0.62, tam=15)
texto(s, 0.6, 5.45, 12.15, 1.3, [
    ("Biblioteca: POSIX Threads — #include <pthread.h> (comum.h:13), compilado com -pthread", {"bala": True}),
    ("Inicializados antes de qualquer pthread_create (main.c:187) e destruídos só depois de todos os joins (main.c:215-222)", {"bala": True}),
], tam=16, espaco=6)
rodape(s)
notas(s, "[Integrante 2] (~40 s) Esta tabela responde a 'onde nasce cada mecanismo'. O mutex é declarado em "
         "comum.h linha 82 e inicializado em main.c linha 131. As quatro variáveis de condição: cv_largada para "
         "o sinal de início, cv_noel onde Noel dorme, cv_elfos onde os elfos esperam a ajuda acabar e cv_renas "
         "onde as renas esperam a viagem. Tudo é criado antes da primeira thread e destruído só depois dos joins.")

# ------------------------------------------------------------------ 13. como o mutex começa
s = novo()
titulo(s, "Como o mutex começa: main.c, linha 131")
codigo(s, 0.6, 1.45, 7.35, 4.6, "main.c", [107, 108, 109, None, 131, 132, 133, 134, None, 136, 137, 138, 139, 140],
       destaque=(131, 138), titulo_cod="main.c — iniciar_oficina(), chamada em main.c:172", tam=13)
texto(s, 8.25, 1.45, 4.5, 4.7, [
    ("pthread_mutex_init(&o->mutex, NULL)", {"negrito": True, "fonte": FONTE_M, "tam": 14, "cor": VERMELHO}),
    ("1º arg: endereço do mutex (campo da Oficina)", {"bala": True}),
    ("2º arg: NULL = atributos padrão (não recursivo, privado ao processo)", {"bala": True}),
    ("Estado inicial: destravado, sem dono — a 1ª thread que der lock entra", {"bala": True, "negrito": True}),
    ("O memset da linha 109 zera os contadores, mas não é a inicialização do mutex pela POSIX", {"bala": True}),
    ("Retorno do init não é verificado (ponto de robustez)", {"bala": True, "cor": CINZA}),
], tam=15, espaco=7)
caixa(s, 0.6, 6.2, 12.15, 0.6, cor=VERDE_CLARO)
texto(s, 0.8, 6.22, 11.8, 0.56, "Linha 138: cv_noel usa CLOCK_MONOTONIC — o prazo do timeout (t0 + 2000 ms, noel.c:83) "
      "é medido no mesmo relógio de t0", tam=15, ancora=MSO_ANCHOR.MIDDLE)
rodape(s)
notas(s, "[Integrante 2] (~45 s) Pergunta certa do professor: como o mutex começa. Ele é inicializado em "
         "iniciar_oficina, main.c linha 131, com pthread_mutex_init, passando o endereço do mutex e NULL, que "
         "significa atributos padrão. Ele começa destravado e sem dono. O memset antes só zera os contadores. "
         "Na linha 138 a cv_noel recebe o relógio monotônico, para o timeout ser medido no mesmo relógio do t0. "
         "Um ponto de melhoria: os retornos dessas funções não são conferidos.")

# ------------------------------------------------------------------ 14. valores iniciais
s = novo()
titulo(s, "Valores iniciais e o que significam")
linhas = [["Mecanismo / variável", "Valor inicial", "Onde", "Significado"],
          ["mutex", "destravado", "main.c:131", "ninguém na seção crítica"],
          ["cv_largada, cv_elfos, cv_renas, cv_noel", "fila vazia", "main.c:132-140", "variável de condição não tem valor"],
          ["largada, threads_prontas", "0, 0", "memset main.c:109", "ninguém começa antes da main dar o sinal"],
          ["total_threads", "1 + 9 + N", "main.c:112", "quantas a largada espera"],
          ["renas_prontas, viagem_iniciada/_concluida", "0, 0, 0", "memset", "nenhuma rena, nenhuma viagem"],
          ["grupos[k].n, .estado", "0, GRUPO_ABERTO", "calloc main.c:116", "todos os grupos vazios e abertos"],
          ["grupo_aberto, grupos_fechados, proximo_grupo", "0, 0, 0", "memset", "1º grupo recebe elfos; fila vazia"],
          ["estado de Noel / abortar", "DORMINDO / 0", "main.c:113 / memset", "sem tarefa; sem timeout"]]
tabela(s, linhas, 0.6, 1.45, [4.45, 1.95, 2.25, 3.5], alt_linha=0.54, tam=14)
texto(s, 0.6, 6.4, 12.15, 0.5, "Numa variável de condição, o \"valor inicial\" que importa é o das variáveis do predicado — "
      "a memória está nelas, não na fila.", tam=15, cor=CINZA)
rodape(s)
notas(s, "[Integrante 2] (~30 s) Mutex começa destravado. Variáveis de condição não têm valor: começam com a fila "
         "vazia. O que tem valor são as variáveis que elas observam, e todas começam em zero: nenhuma rena, "
         "nenhum grupo fechado, viagem não feita, largada não dada. total_threads é 1 + 9 + N, que é quantas "
         "threads a largada espera. Se renas_prontas começasse em 1, a viagem sairia com 8 renas.")

# ------------------------------------------------------------------ 15. seções críticas
s = novo()
titulo(s, "Seções críticas: quem trava e quem solta")
linhas = [["Thread", "lock", "unlock", "Dentro da seção crítica"],
          ["main", "main.c:207", "main.c:213", "espera todas prontas, grava t0, largada = 1"],
          ["Noel", "noel.c:81", "noel.c:145", "laço de decisão inteiro (lê renas_ok/elfos_ok, decide, marca estados)"],
          ["Noel (sleep)", "noel.c:33 / 62", "noel.c:31 / 60", ("solta o mutex só para dormir 5 ms / 3 ms", {"negrito": True})],
          ["Rena", "rena.c:23", "rena.c:25 / 38", "renas_prontas++, avisa Noel se 9ª, espera a viagem"],
          ["Elfo", "elfo.c:27", "elfo.c:29 / 38 / 59", "inscreve-se, fecha o grupo se 3º, espera o fim da ajuda"]]
tabela(s, linhas, 0.6, 1.45, [1.7, 1.8, 2.15, 6.5], alt_linha=0.58, tam=15)
caixa(s, 0.6, 5.15, 5.95, 1.6)
texto(s, 0.8, 5.22, 5.6, 1.5, [
    ("Todo caminho que trava também solta", {"negrito": True, "cor": VERDE}),
    ("o elfo tem 3 saídas (timeout, invasão detectada, normal) e as 3 chamam unlock", {"tam": 14}),
], tam=16)
caixa(s, 6.8, 5.15, 5.95, 1.6, cor=RGBColor(0xFB, 0xEC, 0xEC))
texto(s, 7.0, 5.22, 5.6, 1.5, [
    ("Esquecer um unlock trava tudo", {"negrito": True, "cor": VERMELHO}),
    ("nem o timeout salva: o timedwait de Noel precisa readquirir o mutex para retornar", {"tam": 14}),
], tam=16)
rodape(s)
notas(s, "[Integrante 2] (~40 s) Aqui estão todas as seções críticas. Noel fica com o mutex durante o laço de "
         "decisão e só o solta para simular os 5 ms da viagem ou os 3 ms da ajuda — assim elfos e renas "
         "continuam chegando enquanto ele trabalha. Rena e elfo travam, alteram o estado e esperam. "
         "Lembrar também: pthread_cond_wait solta o mutex enquanto a thread dorme.")

# ------------------------------------------------------------------ 16. padrão wait/signal
s = novo()
titulo(s, "Esperar sem gastar CPU: while + wait")
codigo(s, 0.6, 1.45, 5.6, 1.75, "rena.c", [36, 37, 38], destaque=(36, 37), titulo_cod="quem espera — rena.c", tam=13)
codigo(s, 0.6, 3.4, 5.6, 1.75, "noel.c", [37, None, 41], destaque=(37, 41), titulo_cod="quem avisa — noel.c, preparar_viagem()", tam=13)
passos = [("1", "Com o mutex, testa o predicado: viagem_concluida?"),
          ("2", "Falso → pthread_cond_wait solta o mutex e dorme numa única operação atômica"),
          ("3", "Noel muda o estado (linha 37) e faz broadcast (linha 41)"),
          ("4", "A rena acorda, retrava o mutex e testa de novo (while)"),
          ("5", "Verdadeiro → sai do laço e solta o mutex")]
for i, (n, t) in enumerate(passos):
    y = 1.5 + i * 0.73
    circulo(s, 6.55, y, 0.52, n, cor=VERMELHO if n == "2" else VERDE, tam=15)
    texto(s, 7.2, y - 0.04, 5.55, 0.65, t, tam=15, ancora=MSO_ANCHOR.MIDDLE)
caixa(s, 0.6, 5.45, 12.15, 1.3)
texto(s, 0.85, 5.5, 11.7, 1.2, [
    ("", {"runs": [("Por que while e não if: ", {"negrito": True, "cor": VERDE}),
                   ("acordar espúrio é permitido, e outra thread pode mudar o estado antes de você retravar.", {})]}),
    ("", {"runs": [("A cond var não guarda avisos: ", {"negrito": True, "cor": VERDE}),
                   ("a verdade está nas variáveis protegidas pelo mutex — o sinal só diz \"olhe de novo\".", {})]}),
], tam=16, espaco=6)
rodape(s)
notas(s, "[Integrante 2] (~45 s) Este é o padrão que todas as esperas seguem. A thread trava o mutex e testa a "
         "condição. Se for falsa, pthread_cond_wait solta o mutex e dorme de forma atômica — não há janela "
         "para perder o aviso. Quem muda o estado faz isso com o mutex e depois sinaliza. Ao acordar, a thread "
         "retrava o mutex e testa de novo, por isso é while e não if. Mutex protege o estado; a variável de "
         "condição só coordena a espera.")

# ------------------------------------------------------------------ 17. sequência 9ª rena
s = novo()
titulo(s, "Sequência real: a 9ª rena acorda Noel")
lanes = [("Noel", 1.75), ("9ª rena", 3.65), ("outras renas", 5.35)]
for nome, y in lanes:
    texto(s, 0.4, y, 1.55, 0.5, nome, tam=15, negrito=True, alinh=PP_ALIGN.RIGHT, ancora=MSO_ANCHOR.MIDDLE)
    linha_reta(s, 2.05, y + 0.25, 12.85, y + 0.25, cor=CINZA_BARRA, larg=1.5, tracejada=True)
etapas = [  # (lane, x, texto, cor)
    (0, 2.1, "timedwait\ncv_noel\nnoel.c:101", CINZA),
    (1, 3.35, "lock\nrena.c:23", VERDE),
    (1, 4.6, "contador\n= 9\nrena.c:28", VERDE),
    (1, 5.85, "signal\ncv_noel (l.33)", VERMELHO),
    (0, 7.1, "acorda,\nreavalia\nnoel.c:107, 89", VERDE),
    (0, 8.35, "decide viagem\nnoel.c:117", VERMELHO),
    (0, 9.6, "unlock, dorme\n5 ms, lock\nnoel.c:31-33", LARANJA),
    (0, 10.85, "concluída = 1\nbroadcast\nnoel.c:37, 41", VERMELHO),
]
for k, (lane, x, t, cor) in enumerate(etapas):
    y = lanes[lane][1] - 0.32
    rotulo(caixa(s, x, y, 1.15, 1.15, cor=cor), t, 12)
    circulo(s, x - 0.08, y - 0.12, 0.34, str(k + 1), cor=TINTA, tam=11)
rotulo(caixa(s, 7.1, lanes[1][1] - 0.32, 1.15, 1.15, cor=CINZA), "wait\ncv_renas\nrena.c:37", 12)
rotulo(caixa(s, 10.85, lanes[2][1] - 0.3, 1.9, 1.0, cor=VERDE), "acordam 1 a 1,\nretravam, saem\nrena.c:36-38", 12)
seta(s, 6.45, lanes[1][1] - 0.35, 7.1, lanes[0][1] + 0.6, cor=VERMELHO, larg=2.25)
seta(s, 11.75, lanes[0][1] + 0.85, 11.75, lanes[2][1] - 0.3, cor=VERMELHO, larg=2.25)
texto(s, 0.6, 6.4, 12.15, 0.5, f"Dados reais (E06_R10_rep1): 9ª rena em {br(t_ev(eventos[eventos.execucao == 'E06_R10_rep1'], 'nona_rena'), 3)} ms → "
      f"decisão em {br(t_ev(eventos[eventos.execucao == 'E06_R10_rep1'], 'decisao'), 3)} ms — "
      f"resposta média às renas na referência (E06_R10) ≈ {br(1000 * r06['resposta_renas_media_ms'], 0)} µs", tam=15, cor=CINZA)
rodape(s)
notas(s, "[Integrante 2] (~45 s) Sequência real. 1: Noel não tem trabalho e dorme em cv_noel, o que solta o mutex. "
         "2 e 3: a nona rena trava o mutex e incrementa o contador para 9. 4: sinaliza Noel e vai esperar em "
         "cv_renas, soltando o mutex. 5: Noel acorda, retrava o mutex e reavalia: agora renas_ok é verdadeiro. "
         "6: decide pela viagem na mesma seção crítica. 7: solta o mutex só para dormir os 5 ms. 8: marca "
         "viagem_concluida e faz broadcast; as renas acordam uma de cada vez e saem.")

# ------------------------------------------------------------------ 18. grupos e 4º elfo
s = novo()
titulo(s, "Grupos de 3: o 4º elfo nunca invade")
linhas = [["Elfo", "Ação (com o mutex)", "g0.n", "g1.n", "grupo_aberto", "grupos_fechados"],
          ["0", "entra em g0", "1", "0", "0", "0"],
          ["1", "entra em g0", "2", "0", "0", "0"],
          [("2", {"negrito": True}), ("entra em g0 → PRONTO, signal(cv_noel)", {"negrito": True, "cor": VERMELHO}), "3", "0",
           ("1", {"negrito": True, "cor": VERMELHO}), ("1", {"negrito": True, "cor": VERMELHO})],
          ["3", "entra em g1 (g0 já não é o aberto)", "3", "1", "1", "1"],
          ["4", "entra em g1", "3", "2", "1", "1"],
          ["5", "entra em g1 → PRONTO, signal (último)", "3", "3", "1", "2"]]
tabela(s, linhas, 0.6, 1.45, [0.7, 3.95, 0.8, 0.8, 1.55, 1.8], alt_linha=0.5, tam=14, destaque={3})
codigo(s, 0.6, 5.1, 9.6, 1.7, "elfo.c", [45, 47, 49, 50, 51, 53], destaque=(47, 51, 53), tam=12)
caixa(s, 10.45, 1.45, 2.3, 5.35)
texto(s, 10.6, 1.55, 2.05, 5.15, [
    ("Fila FIFO", {"negrito": True, "cor": VERDE, "tam": 18}),
    ("Noel só vê um grupo quando proximo_grupo < grupos_fechados (noel.c:90)", {}),
    ("e atende g = proximo_grupo++ (noel.c:128)", {}),
    ("O 4º elfo não espera: abre o próximo grupo", {"negrito": True}),
], tam=14, espaco=10)
rodape(s)
notas(s, "[Integrante 2] (~45 s) Como impedimos o quarto elfo de entrar num grupo iniciado: cada grupo tem um id "
         "e o elfo entra sempre no grupo apontado por grupo_aberto. Quando o terceiro elfo se inscreve, na "
         "mesma seção crítica ele marca o grupo como PRONTO, incrementa grupos_fechados e avança grupo_aberto. "
         "O quarto elfo, quando consegue o mutex, já cai no grupo seguinte. Os grupos formam uma fila FIFO, "
         "então também não há starvation entre elfos. Diferente da solução clássica com semáforos, o quarto "
         "elfo não espera: já forma o próximo grupo.")

# ------------------------------------------------------------------ 19. decisão de Noel (fluxo)
s = novo()
titulo(s, "O laço de decisão de Noel")
fl = [(0.6, 1.55, 2.4, 0.95, "lock mutex\nnoel.c:81", VERDE),
      (3.5, 1.55, 2.7, 0.95, "tudo concluído?\nnoel.c:86", CINZA),
      (6.7, 1.55, 2.8, 0.95, "renas_ok, elfos_ok\nnoel.c:89-90", VERDE),
      (10.0, 1.55, 2.75, 0.95, "nada pronto?\nnoel.c:100", CINZA)]
for x, y, w, h, t, c in fl:
    rotulo(caixa(s, x, y, w, h, cor=c), t, 14)
for a, b in ((3.0, 3.5), (6.2, 6.7), (9.5, 10.0)):
    seta(s, a, 2.02, b, 2.02, cor=TINTA)
rotulo(caixa(s, 3.5, 3.0, 2.7, 0.85, cor=TINTA), "sim → ENCERRADO\nbroadcast, unlock", 13)
seta(s, 4.85, 2.5, 4.85, 3.0, cor=TINTA)
rotulo(caixa(s, 10.0, 3.0, 2.75, 0.85, cor=CINZA), "sim → timedwait\nsolta mutex, dorme", 13)
seta(s, 11.37, 2.5, 11.37, 3.0, cor=TINTA)
rotulo(caixa(s, 6.7, 3.0, 2.8, 0.85, cor=VERMELHO), "não → renas_ok?\nnoel.c:117", 14)
seta(s, 10.0, 2.3, 9.5, 3.2, cor=TINTA)
rotulo(caixa(s, 5.0, 4.4, 2.9, 1.05, cor=LARANJA), "sim: preparar_viagem\nunlock · 5 ms · lock\nbroadcast cv_renas", 13)
rotulo(caixa(s, 8.4, 4.4, 2.9, 1.05, cor=AZUL), "não: ajudar_grupo\nproximo_grupo++\n3 ms · broadcast cv_elfos", 13)
seta(s, 7.6, 3.85, 6.6, 4.4, cor=TINTA)
seta(s, 8.6, 3.85, 9.6, 4.4, cor=TINTA)
rotulo(caixa(s, 0.6, 4.4, 3.9, 1.05, cor=VERDE_CLARO), "volta ao topo do laço\ncom o mutex (reavalia tudo)", 14, VERDE)
seta(s, 5.0, 4.92, 4.5, 4.92, cor=VERDE)
seta(s, 2.55, 4.4, 1.8, 2.5, cor=VERDE)
seta(s, 11.37, 3.85, 11.9, 4.2, cor=VERDE)
texto(s, 11.3, 4.2, 1.6, 0.9, "acordou →\ntopo do laço", tam=12, cor=VERDE)
texto(s, 0.6, 5.8, 12.15, 0.9, [
    ("", {"runs": [("Leitura e decisão na mesma seção crítica: ", {"negrito": True, "cor": VERDE}),
                   ("ninguém muda renas_prontas ou a fila entre o teste e a escolha. A ajuda/viagem é simulada fora do "
                    "mutex, mas só Noel volta a decidir.", {})]}),
], tam=16)
rodape(s)
notas(s, "[Integrante 2] (~40 s) O laço de Noel: trava o mutex, verifica se terminou, calcula renas_ok e elfos_ok. "
         "Se nada está pronto, dorme em cv_noel com prazo. Se algo está pronto, decide: renas primeiro. A tarefa "
         "é simulada fora do mutex, e no fim ele volta ao topo do laço e reavalia tudo. O ponto importante: "
         "ler o estado e decidir acontecem sem soltar o mutex.")

# ------------------------------------------------------------------ estados de Noel (v3)
s = novo()
titulo(s, "Estados de Noel e transições")
pilulas = {"P": (1.1, "PREPARANDO", LARANJA), "D": (5.5, "DORMINDO", CINZA), "A": (9.9, "AJUDANDO", AZUL)}
for x, nome, cor in pilulas.values():
    rotulo(caixa(s, x, 1.9, 2.3, 1.0, cor=cor, raio=0.5), nome, 17)
rotulo(caixa(s, 5.5, 3.95, 2.3, 0.75, cor=TINTA, raio=0.5), "ENCERRADO", 16)
texto(s, 5.5, 1.3, 2.3, 0.4, "início · main.c:113", tam=13, cor=CINZA, alinh=PP_ALIGN.CENTER)
seta(s, 6.65, 1.65, 6.65, 1.9, cor=CINZA)
transicoes = [(5.5, 3.4, 2.15, "renas_ok → viagem\nnoel.c:117, 124", True),
              (3.4, 5.5, 2.65, "fim da viagem\nnoel.c:39", False),
              (7.8, 9.9, 2.15, "só elfos_ok → grupo\nnoel.c:117, 129", True),
              (9.9, 7.8, 2.65, "fim da ajuda\nnoel.c:71", False)]
for xa, xb, y, rot, cima in transicoes:
    seta(s, xa, y, xb, y, cor=VERMELHO if cima else VERDE, larg=2.25)
    texto(s, min(xa, xb), 1.3 if cima else 2.72, 2.1, 0.8, rot, tam=13, alinh=PP_ALIGN.CENTER,
          ancora=MSO_ANCHOR.BOTTOM if cima else MSO_ANCHOR.TOP)
seta(s, 6.65, 2.9, 6.65, 3.95, cor=TINTA, larg=2.25)
texto(s, 6.8, 3.3, 3.0, 0.45, "tudo concluído · noel.c:136", tam=13)
fx = faixas("E06_R10_rep1")
esc = linha_do_tempo(s, 2.35, 5.05, 10.35, 0.0, 22.0, fx, "E06_R10_rep1")
for t in range(0, 23, 5):
    x = esc(t)
    linha_reta(s, x, 5.55, x, 5.65, cor=CINZA)
    texto(s, x - 0.3, 5.65, 0.6, 0.3, f"{t} ms" if t == 20 else str(t), tam=12, cor=CINZA, alinh=PP_ALIGN.CENTER)
texto(s, 0.6, 6.1, 12.15, 0.75, [
    ("", {"runs": [("Só a thread Noel muda o estado, sempre com o mutex. ", {"negrito": True, "cor": VERDE}),
                   ("DORMINDO = em timedwait na cv_noel (noel.c:101) ou decidindo no topo do laço; "
                    f"na referência, Noel fica ocupado {br(100 * r06['utilizacao_noel_media'], 1)}% do tempo.", {})]}),
], tam=15)
rodape(s)
notas(s, "[Integrante 2] (~35 s) Os quatro estados do enum EstadoNoel (comum.h:21-26). Noel começa DORMINDO "
         "(main.c:113). Com o mutex, decide: se renas_ok, vai para PREPARANDO; se só elfos_ok, para AJUDANDO. "
         "Ao fim de cada tarefa volta a DORMINDO e reavalia; não há transição direta de AJUDANDO para "
         "PREPARANDO, e é isso que garante que a ajuda não é interrompida. Quando a viagem e todos os grupos "
         "terminam, vai para ENCERRADO e acorda todas as filas. Embaixo, a mesma máquina de estados numa "
         "execução real.")

# ------------------------------------------------------------------ 20. prioridade sem interromper
s = novo()
titulo(s, "Prioridade às renas sem interromper a ajuda")
codigo(s, 0.6, 1.45, 7.25, 2.6, "noel.c", [89, 90, None, 117, None, 123, 126, None, 128, 131], destaque=(89, 117),
       titulo_cod="noel.c — thread_noel(), com o mutex", tam=13)
codigo(s, 0.6, 4.2, 7.25, 1.45, "noel.c", [60, 61, 62], destaque=(61,), titulo_cod="durante a ajuda — ajudar_grupo()", tam=13)
cen = [("Renas prontas ANTES da decisão", "Noel lê as duas demandas e escolhe a viagem (renas_ok)", VERDE),
       ("Renas chegam DURANTE a ajuda", "contam-se e dão signal, mas Noel está em dormir_ate_ms; "
        "ao terminar, volta ao laço e prepara a viagem", LARANJA),
       ("Renas chegam DEPOIS", "Noel atende os grupos e dorme; a 9ª rena o acorda", AZUL)]
for i, (t, d, c) in enumerate(cen):
    y = 1.45 + i * 1.42
    caixa(s, 8.05, y, 4.7, 1.3, cor=VERDE_CLARO)
    circulo(s, 8.2, y + 0.12, 0.45, str(i + 1), cor=c, tam=14)
    texto(s, 8.8, y + 0.1, 3.85, 0.4, t, tam=15, negrito=True, cor=TINTA)
    texto(s, 8.8, y + 0.48, 3.85, 0.8, d, tam=14)
texto(s, 0.6, 5.85, 12.15, 0.95, [
    ("", {"runs": [("Por quê funciona: ", {"negrito": True, "cor": VERDE}),
                   ("só a thread Noel decide; elfos e renas apenas alteram contadores e avisam. A prioridade vale nos "
                    "pontos de decisão (política não preemptiva). Uma rena bloqueada no lock no instante da decisão "
                    "ainda não \"chegou\" — não é violação.", {})]}),
], tam=15)
rodape(s)
notas(s, "[Integrante 2] (~50 s) Como a prioridade é garantida: com o mutex, Noel calcula renas_ok e elfos_ok e "
         "escolhe primeiro as renas, na linha 117. Como não interrompe a ajuda: só a thread Noel decide, e durante "
         "a ajuda ela está dormindo em dormir_ate_ms, sem olhar nada. Se a nona rena chega no meio, ela "
         "incrementa o contador e sinaliza, mas o aviso não tem ouvinte; o estado fica gravado e Noel vê na "
         "volta ao laço. Atenção: o caso 'durante' foi analisado no código; nos parâmetros da matriz as renas "
         "nunca chegaram no meio de uma ajuda.")

# ------------------------------------------------------------------ 21. cenários reais
s = novo()
titulo(s, "Antes, junto ou depois: execuções reais")
t0v, t1v = 4.0, 36.0
xs, ws = 2.35, 10.35
cfgs = [("E06_R05_rep1", "antes (5 ms)"), ("E06_R10_rep1", "junto (10 ms)"), ("E06_R30_rep1", "depois (30 ms)")]
for i, (e, rot) in enumerate(cfgs):
    fx = faixas(e)
    y = 1.75 + i * 1.3
    esc = linha_do_tempo(s, xs, y, ws, t0v, t1v, fx, rot)
    texto(s, min(esc(fx["fim"]) + 0.05, xs + ws - 1.2), y + 0.45, 1.6, 0.35, f"fim {br(fx['fim'], 1)} ms", tam=11, cor=CINZA)
for t in range(5, 36, 5):
    x = xs + (t - t0v) / (t1v - t0v) * ws
    linha_reta(s, x, 5.55, x, 5.65, cor=CINZA)
    texto(s, x - 0.3, 5.65, 0.6, 0.3, str(t), tam=12, cor=CINZA, alinh=PP_ALIGN.CENTER)
linha_reta(s, xs, 5.55, xs + ws, 5.55, cor=CINZA)
texto(s, xs, 5.92, ws, 0.3, "tempo desde o sinal de início (ms)", tam=12, cor=CINZA, alinh=PP_ALIGN.CENTER)
leg = [(LARANJA, "preparando viagem"), (AZUL, "ajudando grupo k"), (CINZA_BARRA, "dormindo")]
for i, (c, t) in enumerate(leg):
    caixa(s, 0.6 + i * 2.6, 6.45, 0.35, 0.25, cor=c, forma=MSO_SHAPE.RECTANGLE)
    texto(s, 1.0 + i * 2.6, 6.37, 2.2, 0.4, t, tam=13)
linha_reta(s, 8.5, 6.58, 8.85, 6.58, cor=RGBColor(0x1B, 0xAF, 0x7A), larg=2, tracejada=True)
texto(s, 8.9, 6.37, 1.6, 0.4, "grupo pronto", tam=13)
linha_reta(s, 10.6, 6.58, 10.95, 6.58, cor=RGBColor(0x62, 0x50, 0xD6), larg=2.5)
texto(s, 11.0, 6.37, 1.8, 0.4, "9ª rena", tam=13)
rodape(s)
notas(s, "[Integrante 3] (~40 s) Três execuções reais, lidas do eventos.csv. Antes: a viagem acontece de 5 a 10 ms, "
         "Noel está livre quando cada grupo fecha. Junto: a 9ª rena chega a 10 ms, a viagem ocupa até 15 ms e "
         "os dois grupos ficam prontos nesse intervalo e esperam — é a disputa. Depois: os grupos são atendidos "
         "primeiro e Noel dorme até as renas chegarem em 30 ms. Em nenhuma execução uma ajuda foi interrompida.")

# ------------------------------------------------------------------ 22. ordens diferentes
s = novo()
titulo(s, "Outras ordens, mesmo resultado", apoio=True)
linhas = [["Ordem de execução", "O que o código faz", "Resultado"],
          ["3º elfo dá signal com Noel ocupado (preparando)", "o signal não acorda ninguém, mas grupos_fechados++ ficou gravado",
           "Noel vê o grupo ao voltar ao laço (real: grupo 2 pronto em 15,06 ms)"],
          ["9ª rena e 3º elfo avisam antes de Noel rodar", "Noel acorda uma vez e lê os dois prontos", ("escolhe renas (disputa do teste)", {"negrito": True})],
          ["9ª rena bloqueada no lock enquanto Noel decide", "para o programa a rena ainda não chegou", "ajuda o grupo; depois a viagem — não é violação"],
          ["Noel acorda espuriamente", "continue → reavalia (noel.c:107)", "volta a dormir"],
          ["Elfo do grupo 2 acorda no broadcast do grupo 1", "testa o próprio grupo (elfo.c:57)", "volta a dormir"],
          ["Elfo 0 chega antes da 9ª rena (real: 10,080 × 10,091 ms)", "quem pega o mutex primeiro se registra primeiro", "decisão em 10,108 ms: só renas prontas → viagem"]]
tabela(s, linhas, 0.6, 1.45, [3.9, 4.3, 3.95], alt_linha=0.72, tam=14)
rodape(s)
notas(s, "[Integrante 2] APOIO. Se perguntarem 'e se as threads rodarem em outra ordem?': a decisão nunca se baseia "
         "no sinal recebido, e sim no estado lido com o mutex. Por isso aviso perdido, acordar espúrio ou outra "
         "thread chegando antes não quebram nada.")

# ------------------------------------------------------------------ 23. correta × ingênua (v3)
s = novo()
titulo(s, "Correta × ingênua: mesmo cenário")
ev_ok = pd.read_csv(D / "teste_prioridade" / "eventos.csv")
xs, ws, t0v, t1v = 2.35, 10.35, 10.0, 43.0
for i, (df, rot) in enumerate([(ev_ok, "correta"), (ing_ev, "ingênua")]):
    fx = faixas(df["execucao"].iloc[0], df)
    esc = linha_do_tempo(s, xs, 1.7 + i * 1.1, ws, t0v, t1v, fx, rot)
    texto(s, min(esc(fx["fim"]) + 0.05, xs + ws - 1.2), 2.17 + i * 1.1, 1.6, 0.35, f"fim {br(fx['fim'], 1)} ms",
          tam=11, cor=CINZA)
for t in range(10, 44, 5):
    x = esc(t)
    linha_reta(s, x, 3.95, x, 4.05, cor=CINZA)
    texto(s, x - 0.3, 4.05, 0.6, 0.3, str(t), tam=12, cor=CINZA, alinh=PP_ALIGN.CENTER)
linha_reta(s, xs, 3.95, xs + ws, 3.95, cor=CINZA)
texto(s, xs, 4.35, ws, 0.35, "ms desde o sinal de início · ./simulacao --elfos 6 --renas-ms 30 --teste-prioridade [--ingenua]",
      tam=12, cor=CINZA, alinh=PP_ALIGN.CENTER)
cards = [(f"{int(ing['violacoes_prioridade'])} violações", VERMELHO,
          "a ingênua ajudou g1 e g2 com as 9 renas já prontas"),
         (f"{br(ing['resposta_renas_ms'], 1)} ms × {br(tp['resposta_renas_ms'] * 1000, 0)} µs", VERMELHO,
          "resposta às renas: ingênua × correta"),
         ("noel.c:117", VERDE, "única mudança: !elfos_ok no lugar de renas_ok; o detector (l. 118-119) deu 0 na matriz")]
for i, (v, c, d) in enumerate(cards):
    x = 0.6 + i * 4.1
    caixa(s, x, 4.95, 3.85, 1.85)
    texto(s, x + 0.2, 5.0, 3.5, 0.7, v, tam=28, negrito=True, cor=c, fonte=FONTE_T)
    texto(s, x + 0.2, 5.7, 3.5, 1.05, d, tam=14)
rodape(s)
notas(s, "[Integrante 2] (~40 s) Mesmo cenário, mesma flag de teste, só a regra de decisão muda. Em cima, a solução "
         "correta: quando a 9ª rena chega, por volta de 30 ms, a primeira decisão é a viagem, e os grupos vêm depois. "
         "Embaixo, a versão ingênua, que atende elfos primeiro: ajudou os dois grupos com as renas esperando e só "
         "então preparou a viagem. O programa contou as duas violações, e a resposta às renas passou de "
         "microssegundos para mais de 6 ms. Isso mostra que o detector funciona, então o zero da matriz tem "
         "significado.")

# ------------------------------------------------------------------ 24. demonstração (v1)
s = novo()
titulo(s, "Demonstração: disputa real")
caixa(s, 0.6, 1.5, 12.15, 3.75, cor=FUNDO_COD)
linhas_saida = []
for l in saida_teste:
    linhas_saida += textwrap.wrap(l, 96, subsequent_indent="    ", break_on_hyphens=False) or [""]
texto(s, 0.85, 1.65, 11.7, 3.6, [(l, {"cor": COD_OK if "OK" in l or "PASSOU" in l else COD_TXT}) for l in linhas_saida],
      tam=14, fonte=FONTE_M, espaco=1)
passos = [("1", "Noel fica \"atrasado\": espera em cv_noel até as duas demandas ficarem prontas (noel.c:94-98)"),
          ("2", "Grupos prontos em 12 e 15 ms; 9ª rena em ~30 ms; a 1ª decisão é a viagem"),
          ("3", f"{int(tp['concluidos'])}/{int(tp['previstos'])} elfos atendidos, 0 violações, saída em dados/teste_prioridade/")]
for i, (n, txt) in enumerate(passos):
    x = 0.6 + i * 4.1
    circulo(s, x, 5.65, 0.6, n, cor=VERMELHO, tam=16)
    texto(s, x + 0.75, 5.5, 3.25, 1.35, txt, tam=14, ancora=MSO_ANCHOR.MIDDLE)
rodape(s)
notas(s, "[Integrante 2] (~1 min 30 s) Rodar ao vivo: cd src && ./simulacao --elfos 6 --renas-ms 30 --rep 1 "
         "--semente 11 --out ../dados/teste_prioridade/ --teste-prioridade. Neste modo Noel só é liberado "
         "quando as renas e pelo menos um grupo estão prontos — isso cria a disputa de propósito, sem sleep: "
         "Noel espera na própria cv_noel. A saída mostra disputa = SIM, primeira decisão = renas, 6 de 6 elfos "
         "e zero violações.")

# ================================================================== PROPRIEDADES
divisor("Propriedades", "Deadlock, starvation, espera ocupada e o que caracteriza uma boa solução", 4)
notas(prs.slides[-1], "[Integrante 3] Transição para as propriedades da solução.")

# ------------------------------------------------------------------ 26. deadlock etc.
s = novo()
titulo(s, "Deadlock, starvation e corrida")
cards = [("Deadlock", "threads esperando umas pelas outras para sempre (Coffman: posse e espera + espera circular…)",
          "Não ocorre: 1 único mutex, sem lock aninhado; quem espera em cond var solta o mutex; todo predicado tem quem avise",
          VERDE),
         ("Starvation", "uma thread nunca progride porque outras sempre passam na frente",
          "Não na versão finita: 1 viagem e grupos em FIFO (noel.c:128). Risco numa versão contínua: renas sempre ganhariam",
          LARANJA),
         ("Espera ocupada", "girar num laço testando uma condição, gastando CPU",
          "Não ocorre: toda espera é pthread_cond_wait/timedwait; sleeps só simulam durações",
          VERDE),
         ("Condição de corrida", "resultado depende do entrelaçamento",
          "Descartada por inspeção (todo estado mutável com mutex); não verificada com TSan/Helgrind",
          LARANJA)]
for i, (t, d, aqui, c) in enumerate(cards):
    x, y = 0.6 + (i % 2) * 6.2, 1.45 + (i // 2) * 2.7
    caixa(s, x, y, 5.95, 2.5, cor=VERDE_CLARO)
    circulo(s, x + 5.3, y + 0.15, 0.5, "✓" if c == VERDE else "!", cor=c, tam=18)
    texto(s, x + 0.25, y + 0.1, 4.9, 0.45, t, tam=19, negrito=True, cor=VERDE)
    texto(s, x + 0.25, y + 0.55, 4.9, 0.75, d, tam=14, cor=CINZA)
    texto(s, x + 0.25, y + 1.3, 5.5, 1.15, [("", {"runs": [("Aqui: ", {"negrito": True}), (aqui, {})]})], tam=14)
rodape(s)
notas(s, "[Integrante 3] (~50 s) Deadlock: não há, porque existe um único mutex, ninguém segura um recurso esperando "
         "outro, e quem espera numa variável de condição solta o mutex. Starvation: na versão finita não há — só "
         "uma viagem e os grupos são atendidos em ordem; mas se as renas voltassem sempre, a prioridade absoluta "
         "deixaria os elfos esperando para sempre; a mitigação seria aging ou cota. Espera ocupada: nenhuma. "
         "Corrida: descartada pela análise do código, mas não temos ferramenta como ThreadSanitizer para provar.")

# ------------------------------------------------------------------ 27. princípios
s = novo()
titulo(s, "Princípios de uma boa solução")
linhas = [["Critério", "Atende?", "Evidência no código"],
          ["Exclusão mútua", ("sim", {"negrito": True, "cor": VERDE}), "todo estado mutável só com o mutex (comum.h:78)"],
          ["Progresso", ("sim", {"negrito": True, "cor": VERDE}), "se renas_ok ou elfos_ok, Noel decide (noel.c:100-132)"],
          ["Espera limitada", ("sim (finita)", {"negrito": True, "cor": VERDE}), "≤ 1 viagem + fila FIFO de grupos"],
          ["Sem hipótese de velocidade", ("sim", {"negrito": True, "cor": VERDE}), "toda espera é por predicado; sleeps só simulam"],
          ["Sem espera ocupada", ("sim", {"negrito": True, "cor": VERDE}), "cond_wait / timedwait em todas as esperas"],
          ["Sem deadlock", ("sim", {"negrito": True, "cor": VERDE}), "1 mutex, não recursivo, sem lock aninhado"],
          ["Robustez", ("parcial", {"negrito": True, "cor": LARANJA}), "retornos de init não verificados (main.c:131-139)"]]
tabela(s, linhas, 0.6, 1.45, [3.0, 1.6, 4.4], alt_linha=0.6, tam=15)
caixa(s, 9.85, 1.45, 2.9, 4.8, cor=VERDE)
texto(s, 10.0, 1.55, 2.65, 4.6, [
    ("Poderia ser melhor", {"negrito": True, "tam": 18}),
    ("conferir retornos de pthread_*_init", {"bala": True}),
    ("prazo também na espera da largada (main.c:208)", {"bala": True}),
    ("cond var por grupo (evita acordar elfos de outros grupos)", {"bala": True}),
    ("versão contínua: aging / cota para elfos", {"bala": True}),
], tam=14, cor=BRANCO, espaco=7)
rodape(s)
notas(s, "[Integrante 3] (~40 s) Os critérios clássicos: exclusão mútua, progresso, espera limitada, não depender "
         "de velocidade, e ainda sem espera ocupada e sem deadlock. Atendemos todos na versão finita. Robustez é "
         "parcial: não conferimos os retornos das funções de inicialização. Melhorias: conferir retornos, prazo "
         "na largada, uma variável de condição por grupo e, numa versão contínua, aging para os elfos.")

# ================================================================== RESULTADOS
divisor("Testes e resultados", "Método, métricas, os quatro gráficos e os limites do que eles provam", 5)
notas(prs.slides[-1], "[Integrante 3] Transição para os resultados.")

# ------------------------------------------------------------------ 29. método
s = novo()
titulo(s, "Método: matriz, métricas e testes")
linhas = [["Config.", "Elfos", "Renas", "Papel"],
          ["E06_R10", "6", "10 ms (junto)", "referência"],
          ["E03_R10 · E12_R10", "3 · 12", "10 ms", "conjunto 1: varia elfos"],
          ["E06_R05 · E06_R30", "6", "5 · 30 ms", "conjunto 2: varia renas"]]
tabela(s, linhas, 0.6, 1.45, [2.3, 1.0, 1.6, 2.4], alt_linha=0.52, tam=14)
texto(s, 0.6, 3.7, 7.3, 0.4, f"5 configurações × 5 repetições = {n_exec} execuções · sementes 11…55 = id da repetição "
      "(sem aleatoriedade)", tam=14, cor=CINZA)
texto(s, 0.6, 4.2, 7.3, 2.6, [
    ("Métricas", {"negrito": True, "cor": VERDE, "tam": 17}),
    ("Vazão = pedidos atendidos / T (s)", {"bala": True}),
    ("Espera = início da ajuda − pedido (elfo.c:32 → noel.c:56)", {"bala": True}),
    ("p95 = posição ⌈0,95·n⌉ das esperas ordenadas — com n = 3 ou 6, é o máximo", {"bala": True}),
    ("Resposta às renas = início da preparação − 9ª rena", {"bala": True}),
], tam=15, espaco=5)
caixa(s, 8.2, 1.45, 4.55, 5.3)
texto(s, 8.4, 1.55, 4.2, 5.1, [
    ("Testes além da matriz", {"negrito": True, "cor": VERDE, "tam": 17}),
    (f"Piloto: {len(piloto)} execuções, maior T = {br(piloto['T_ms'].max(), 1)} ms → timeout 2000 ms", {"bala": True}),
    (f"Timeout forçado (5 ms): status {tt['status']}, sem travar", {"bala": True}),
    ("--teste-prioridade: PASSOU", {"bala": True}),
    (f"--ingenua: {int(ing['violacoes_prioridade'])} violações detectadas", {"bala": True}),
    (f"Estresse: {int((est['status'] == 'ok').sum())}/{len(est)} ok", {"bala": True}),
    ("Tempo medido a partir do sinal de início comum (CLOCK_MONOTONIC); CSVs gravados só após os joins", {"bala": True, "cor": CINZA}),
], tam=14, espaco=6)
rodape(s)
notas(s, "[Integrante 3] (~40 s) Rodamos 5 configurações com 5 repetições cada: a referência com 6 elfos e renas "
         "junto, um conjunto variando os elfos e outro variando a chegada das renas. As métricas são vazão, "
         "espera dos elfos com média, p95 e máximo, e resposta às renas. Atenção: com 3 ou 6 amostras o p95 é o "
         "próprio máximo. Além disso: piloto para escolher o timeout, timeout forçado, teste de prioridade, "
         "versão ingênua e 300 execuções de estresse.")

# ------------------------------------------------------------------ 30. G1
s = novo()
titulo(s, "G1 · Mais elfos, mais vazão")
imagem(s, G / "G1_vazao_elfos.png", 0.6, 1.4, h=5.4)
texto(s, 9.0, 1.45, 3.8, 1.1, f"{br(r12['vazao_media_pedidos_s'], 0)}", tam=54, negrito=True, cor=VERDE, fonte=FONTE_T)
texto(s, 9.0, 2.5, 3.8, 0.5, "pedidos/s com 12 elfos", tam=16, cor=CINZA)
texto(s, 9.0, 3.1, 3.8, 3.7, [
    ("Eixo x: nº de elfos · eixo y: pedidos/s; ponto = média de 5, barra = mín–máx; renas fixas em 10 ms", {"tam": 13, "cor": CINZA}),
    (f"{br(r03['vazao_media_pedidos_s'], 0)} → {br(r06['vazao_media_pedidos_s'], 0)} → {br(r12['vazao_media_pedidos_s'], 0)} pedidos/s", {"bala": True}),
    ("Previsão T ≈ 15 + 3·N/3 ms: hipótese confirmada (~2% abaixo)", {"bala": True}),
    ("Explica: fila FIFO atende grupos em sequência; os 15 ms iniciais pesam menos", {"bala": True}),
    ("Diferenças > 100 pedidos/s ≫ faixa mín–máx", {"bala": True}),
], tam=15, espaco=7)
rodape(s)
notas(s, "[Integrante 3] (~40 s) Eixo x: quantidade de elfos; eixo y: pedidos atendidos por segundo; cada ponto é a "
         "média de 5 execuções e a barra vai do mínimo ao máximo. A vazão cresce porque os 10 ms até o primeiro "
         "elfo e os 5 ms da viagem são custo fixo, diluído quando há mais grupos; a fila FIFO atende os grupos "
         "um atrás do outro. Ficou cerca de 2% abaixo da previsão por causa da latência dos sleeps, e a "
         "variação entre repetições é muito menor que a diferença entre os níveis.")

# ------------------------------------------------------------------ 31. G2
s = novo()
titulo(s, "G2 · O preço da prioridade")
imagem(s, G / "G2_p95_renas.png", 0.6, 1.3, w=10.4)
for i, (v, rot, c) in enumerate([(f"{br(r06['espera_p95_ms_media_execucoes'], 1)} ms", "p95 · renas junto", VERMELHO),
                                 (f"{br(a05['espera_p95_ms_media_execucoes'], 1)} ms", "p95 · antes ou depois", VERDE),
                                 ("≈ 20 µs", "resposta às renas", VERDE)]):
    texto(s, 11.1, 1.45 + i * 1.45, 1.7, 0.6, v, tam=26, negrito=True, cor=c, fonte=FONTE_T)
    texto(s, 11.1, 2.05 + i * 1.45, 1.7, 0.6, rot, tam=13, cor=CINZA)
texto(s, 0.6, 6.0, 12.15, 0.85, [
    ("", {"runs": [("Leitura: ", {"negrito": True, "cor": VERDE}),
                   ("só com renas junto a viagem (10–15 ms) cai sobre a formação do grupo 1. Diferença de ~3 ms ≫ "
                    "variação < 0,1 ms. Esquerda: p95 dos elfos (ms); direita: resposta às renas (µs); 6 elfos, 5 execuções.", {})]}),
], tam=15)
rodape(s)
notas(s, "[Integrante 3] (~40 s) Painel esquerdo: categorias de chegada das renas no eixo x, p95 da espera dos "
         "elfos no eixo y. São categorias, por isso os pontos não são ligados. Quando as renas chegam junto, a "
         "viagem ocupa Noel justamente enquanto o primeiro grupo se forma, e o p95 sobe para cerca de 5 ms; "
         "antes ou depois, a espera é só o tempo de completar o grupo, uns 2 ms. Painel direito, separado como "
         "pede o enunciado: as renas são atendidas em cerca de 20 microssegundos. É o efeito da prioridade.")

# ------------------------------------------------------------------ 32. G3
s = novo()
titulo(s, "G3 · O atraso se propaga sem crescer")
imagem(s, G / "G3_p95_grupo.png", 0.6, 1.4, h=5.4)
texto(s, 9.0, 1.45, 3.8, 5.3, [
    ("Eixo x: grupo atendido (1, 2) · eixo y: p95 da espera dos membros; referência, 5 execuções × 3 elfos = 15 amostras/grupo", {"tam": 13, "cor": CINZA}),
    (f"Grupo 1: {br(g3[1][0], 2)} ms ({br(g3[1][1], 2)}–{br(g3[1][2], 2)})", {"bala": True, "negrito": True}),
    (f"Grupo 2: {br(g3[2][0], 2)} ms ({br(g3[2][1], 2)}–{br(g3[2][2], 2)})", {"bala": True, "negrito": True}),
    ("G1 espera a viagem; G2 espera a ajuda ao G1", {"bala": True}),
    ("Grupos chegam a cada 3 ms e cada ajuda dura 3 ms: a fila não cresce", {"bala": True}),
    ("Intuição \"o 2º espera mais\" não se confirmou", {"bala": True, "cor": VERMELHO}),
    ("p95 de 3 amostras = máximo", {"bala": True, "cor": CINZA}),
], tam=15, espaco=7)
rodape(s)
notas(s, "[Integrante 3] (~35 s) Na referência, os dois grupos têm praticamente o mesmo p95. Esperávamos que o "
         "segundo esperasse mais, mas o primeiro espera a viagem e o segundo espera a ajuda ao primeiro; como "
         "os grupos chegam a cada 3 ms e cada ajuda dura 3 ms, o atraso se propaga sem acumular. Dizer que a "
         "intuição não se confirmou mostra que interpretamos o dado em vez de forçar a hipótese.")

# ------------------------------------------------------------------ 33. G4
s = novo()
titulo(s, "G4 · A disputa na linha do tempo")
imagem(s, G / "G4_linha_tempo.png", 0.6, 1.4, w=12.15)
fx = faixas("E06_R10_rep1")
texto(s, 0.6, 6.25, 12.15, 0.6, f"Execução E06_R10_rep1 · 9ª rena {br(fx['nona'], 2)} ms · viagem até {br(fx['prep'][0][1], 2)} ms · "
      f"grupos prontos {br(fx['prontos'][0][0], 2)} e {br(fx['prontos'][1][0], 2)} ms esperam (hachura) sem interromper a viagem",
      tam=15, cor=TINTA)
rodape(s)
notas(s, "[Integrante 3] (~35 s) Eixo x: tempo em ms desde o sinal de início, mostrando o trecho de 8 a 23 ms. Faixa "
         "de cima: estado de Noel. Faixas de baixo: cada grupo, com a hachura indicando o tempo pronto e esperando. "
         "A nona rena chega em 10 ms, a viagem vai até 15, os dois grupos ficam prontos nesse intervalo e entram "
         "na fila; depois Noel trabalha sem pausa.")

# ------------------------------------------------------------------ 34. observação × garantia
s = novo()
titulo(s, "Testes mostram × código garante")
caixa(s, 0.6, 1.45, 5.95, 3.4)
texto(s, 0.85, 1.55, 5.5, 4.4, [
    ("Observação experimental", {"negrito": True, "cor": VERDE, "tam": 20}),
    (f"{n_ok}/{n_exec} execuções válidas, {viol} violações", {"bala": True}),
    (f"{int((est['status'] == 'ok').sum())}/{len(est)} execuções de estresse sem travar", {"bala": True}),
    ("teste de prioridade passou; ingênua foi detectada", {"bala": True}),
    ("Vale para as ordens que ocorreram nestas execuções, nesta máquina", {"bala": True, "negrito": True}),
], tam=16, espaco=9)
caixa(s, 6.8, 1.45, 5.95, 3.4, cor=VERDE)
texto(s, 7.05, 1.55, 5.5, 4.4, [
    ("Garantia por argumento", {"negrito": True, "tam": 20}),
    ("todo estado mutável só com o mutex → sem corrida", {"bala": True}),
    ("leitura + decisão na mesma seção crítica → prioridade", {"bala": True}),
    ("só Noel decide, sem olhar nada durante a ajuda → sem interrupção", {"bala": True}),
    ("1 mutex, waits em laço com predicado → sem deadlock", {"bala": True}),
], tam=16, cor=BRANCO, espaco=9)
texto(s, 0.6, 5.1, 12.15, 0.6, "\"Testes mostram a presença de erros, não a ausência.\" — algumas invariantes (ex.: noel.c:111) "
      "nunca disparam por construção; sem TSan/Helgrind disponíveis.", tam=14, cor=CINZA)
rodape(s)
notas(s, "[Integrante 3] (~35 s) Cuidado ao interpretar: os testes mostram que nas execuções observadas as regras "
         "valeram. Não provam que nunca vão falhar. A garantia vem do argumento sobre o código: estado só com "
         "mutex, decisão na mesma seção crítica da leitura, só Noel decide. Algumas checagens de invariante nunca "
         "podem disparar por construção, então o zero delas sozinho não prova nada; o que mostra que o detector "
         "funciona é a versão ingênua.")

# ------------------------------------------------------------------ 35. conclusões (v1 revisado)
s = novo(VERDE)
texto(s, 0.6, 0.35, 12.1, 0.9, "Conclusões e limitações", tam=34, cor=BRANCO, fonte=FONTE_T, negrito=True)
stats = [(f"{n_ok}/{n_exec}", "execuções válidas"), (str(viol), "violações na matriz"),
         (f"{int((est['status'] == 'ok').sum())}/{len(est)}", "execuções de estresse ok")]
for i, (v, rot) in enumerate(stats):
    x = 0.6 + i * 4.1
    texto(s, x, 1.4, 3.8, 1.1, v, tam=50, negrito=True, cor=BRANCO, fonte=FONTE_T)
    texto(s, x, 2.5, 3.8, 0.5, rot, tam=16, cor=BRANCO)
texto(s, 0.6, 3.3, 6.0, 3.6, [
    ("Como funciona", {"negrito": True, "tam": 20}),
    ("1 mutex protege o estado; 4 cond vars fazem esperar sem gastar CPU", {"bala": True}),
    ("Fila de grupos com id: o 3º elfo fecha o grupo dentro do lock", {"bala": True}),
    ("Só Noel decide, com o mutex: renas primeiro, sem interromper", {"bala": True}),
    ("Vazão cresce com N; p95 só sobe quando a viagem coincide com o 1º grupo", {"bala": True}),
], tam=16, cor=BRANCO, espaco=7)
texto(s, 6.85, 3.3, 5.9, 3.6, [
    ("Limitações", {"negrito": True, "tam": 20}),
    ("Cenário quase determinístico: pouca variação", {"bala": True}),
    ("Latência de timers (0,05–0,5 ms) entra nas medidas", {"bala": True}),
    ("p95 de 3 ou 6 amostras = máximo", {"bala": True}),
    ("Sem TSan/Helgrind; retornos de init não verificados", {"bala": True}),
    ("Versão contínua: risco de starvation dos elfos", {"bala": True}),
], tam=16, cor=BRANCO, espaco=7)
rodape(s, escuro=True)
notas(s, "[Integrante 3] (~40 s) Resumo: um mutex protege todo o estado, quatro variáveis de condição fazem as "
         "threads esperarem sem gastar CPU, a fila de grupos impede a invasão e a decisão de Noel, feita com o "
         "mutex, garante a prioridade sem interromper a ajuda. Resultados: 25 de 25 válidas, nenhuma violação, "
         "300 de estresse. Limitações: cenário quase determinístico, latência dos timers nas medidas, p95 de "
         "poucas amostras, sem ferramenta de detecção de corrida e risco de starvation numa versão contínua. "
         "Obrigado, perguntas?")

# ------------------------------------------------------------------ 36. apêndice: respostas rápidas
def titulo_de(sl):
    return next((sh.text_frame.text for sh in sl.shapes if sh.name == "Título"), "")



s = novo()
titulo(s, "Respostas rápidas para a banca", apoio=True)
linhas = [["Pergunta", "Resposta curta", "Slide"],
          ["Como o mutex começa? Qual linha?", "pthread_mutex_init(&o->mutex, NULL) em main.c:131, destravado e sem dono", ", ".join(str(i + 1) for i, sl in enumerate(prs.slides) if any(titulo_de(sl).startswith(k) for k in ('Como o mutex começa',)))],
          ["Mutex, semáforo ou ambos?", "1 mutex + 4 variáveis de condição; nenhum semáforo", ", ".join(str(i + 1) for i, sl in enumerate(prs.slides) if any(titulo_de(sl).startswith(k) for k in ('Mutex, semáforo', 'Os 5 mecanismos')))],
          ["Valor inicial de cada mecanismo?", "mutex destravado; cond vars sem valor (fila vazia); predicados em 0", ", ".join(str(i + 1) for i, sl in enumerate(prs.slides) if any(titulo_de(sl).startswith(k) for k in ('Valores iniciais',)))],
          ["Por que a thread espera e o que a libera?", "predicado falso → cond_wait solta o mutex e dorme; outra thread muda o estado e sinaliza", ", ".join(str(i + 1) for i, sl in enumerate(prs.slides) if any(titulo_de(sl).startswith(k) for k in ('Esperar sem gastar', 'Sequência real')))],
          ["Como a prioridade é garantida?", "Noel lê renas_ok e elfos_ok com o mutex e testa renas primeiro (noel.c:117)", ", ".join(str(i + 1) for i, sl in enumerate(prs.slides) if any(titulo_de(sl).startswith(k) for k in ('O laço de decisão', 'Prioridade às renas')))],
          ["Como o 4º elfo é barrado?", "o 3º fecha o grupo e avança grupo_aberto na mesma seção crítica (elfo.c:45-51)", ", ".join(str(i + 1) for i, sl in enumerate(prs.slides) if any(titulo_de(sl).startswith(k) for k in ('Grupos de 3',)))],
          ["Há deadlock ou starvation?", "não: 1 mutex, esperas soltam o lock; FIFO e 1 viagem. Contínua: risco", ", ".join(str(i + 1) for i, sl in enumerate(prs.slides) if any(titulo_de(sl).startswith(k) for k in ('Deadlock',)))]]
tabela(s, linhas, 0.6, 1.45, [3.5, 7.45, 1.2], alt_linha=0.66, tam=14)
rodape(s)
notas(s, "APOIO. Cola para perguntas: cada linha aponta o slide onde está a explicação completa.")

# ------------------------------------------------------------------ perguntas prováveis nas notas (vault)
PERGUNTAS = {
    "Sincronização: quando": ("Threads e processos sincronizam do mesmo jeito?",
                              "Os conceitos são os mesmos; entre processos é preciso memória compartilhada e mecanismos "
                              "marcados como compartilháveis (PTHREAD_PROCESS_SHARED). Aqui são threads de um processo."),
    "Condição de corrida": ("Dê um exemplo de entrelaçamento ruim.",
                            "Duas renas leem 7 e gravam 8: o contador nunca chega a 9 e Noel nunca prepara a viagem."),
    "Por que um if": ("Se o if está dentro do mutex, ele ainda serve para quê?",
                      "É uma asserção defensiva (elfo.c:36). Com o código atual nunca dispara; se a lógica mudasse, "
                      "contaria uma violação em vez de corromper o grupo."),
    "Mutex, semáforo": ("Um semáforo inicializado com 1 é igual a um mutex? Por que não usaram semáforos?",
                        "Faz exclusão mútua, mas não tem dono. Não usamos porque Noel espera um predicado composto e "
                        "precisa ler as duas demandas na mesma seção crítica."),
    "O problema:": ("Noel seria preemptivo ou não preemptivo?",
                    "Não preemptivo: decide só entre tarefas, no topo do laço (noel.c:85)."),
    "Os 5 mecanismos": ("Variável de condição sozinha resolve?",
                        "Não: pthread_cond_wait exige o mutex travado, e o predicado do while é protegido por ele."),
    "Como o mutex começa": ("E se uma thread usasse o mutex antes da linha 131? Por que CLOCK_MONOTONIC?",
                            "Seria comportamento indefinido; não ocorre porque as threads nascem em main.c:187-204. "
                            "MONOTONIC porque t0 usa esse relógio e o de tempo real pode ser ajustado."),
    "Valores iniciais": ("Na variável de condição, um valor inicial errado faria diferença?",
                         "Ela não tem valor; o que pode estar errado é o predicado. Ex.: largada = 1 desde o início faria "
                         "as threads começarem antes de t0."),
    "Esperar sem gastar": ("E se o signal acontecer antes de a thread começar a esperar?",
                           "Ele se perde, mas o estado já mudou e a thread testa o predicado antes de dormir. Real: "
                           "grupo 2 pronto em 15,061 ms com Noel preparando."),
    "Estados de Noel": ("A utilização de 32% em E06_R30 é ruim?",
                        "Não indica ineficiência: Noel espera as renas, que chegam tarde. A ociosidade vem do cenário."),
    "Prioridade às renas": ("Se Noel solta o mutex durante a ajuda, outra thread pode roubar o grupo?",
                            "Não: só Noel executa ajudar_grupo; o grupo está EM_AJUDA (noel.c:51) e já saiu da fila "
                            "(noel.c:128)."),
    "Deadlock": ("O timeout não é admitir que pode haver deadlock?",
                 "Não: é rede de segurança pedida no enunciado. Limitação: não cobre um mutex nunca liberado."),
    "Princípios": ("Um único mutex não é um gargalo?",
                   "Com 22 threads e seções de microssegundos, não (resposta ~20 µs). Com milhares, separar locks, "
                   "cuidando da ordem de aquisição."),
    "Método": ("Por que só 5 repetições?",
               "É o que o enunciado pede, e a variação é muito menor que as diferenças entre configurações."),
    "G3": ("O p95 de 3 amostras faz sentido?", "Com n = 3, teto(0,95·3) = 3: o p95 é o máximo. Por isso o gráfico "
           "mostra os pontos individuais."),
    "Testes mostram": ("Os resultados provam que a solução está correta?",
                       "Não provam: mostram as regras valendo nas execuções observadas. A correção vem do argumento "
                       "sobre o código; a ingênua mostra que o detector funciona."),
}


for sl in prs.slides:
    for chave, (q, r) in PERGUNTAS.items():
        if titulo_de(sl).startswith(chave):
            tf = sl.notes_slide.notes_text_frame
            tf.text = tf.text + f"\n\nPergunta provável do professor: {q}\nResposta: {r}"

prs.save(RAIZ / "slides.pptx")
print(f"slides.pptx gerado: {len(prs.slides)} slides")
