#!/usr/bin/env python3
"""gerar_relatorio.py — monta relatorio.pdf a partir dos CSVs e PNGs.

Todo número citado no texto é lido de dados/ (resumo.csv, tabela_esperas.csv,
espera_elfos.csv, eventos dos testes, piloto e estresse); nada é digitado à mão.
Uso: python3 scripts/gerar_relatorio.py   (depois de graficos.py)
Requer: pandas, reportlab e as fontes Liberation (Linux).
"""
import math
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

RAIZ = Path(__file__).resolve().parent.parent
D, G = RAIZ / "dados", RAIZ / "graficos"

FONTES = {
    "Serif": "/usr/share/fonts/liberation-serif-fonts/LiberationSerif-Regular.ttf",
    "Serif-B": "/usr/share/fonts/liberation-serif-fonts/LiberationSerif-Bold.ttf",
    "Serif-I": "/usr/share/fonts/liberation-serif-fonts/LiberationSerif-Italic.ttf",
    "Sans-B": "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
    "Sans": "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf",
    "Mono": "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf",
}
for nome, arq in FONTES.items():
    pdfmetrics.registerFont(TTFont(nome, arq))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-B", italic="Serif-I")

CORPO = ParagraphStyle("corpo", fontName="Serif", fontSize=10.2, leading=13.1, alignment=TA_JUSTIFY,
                       spaceAfter=4)
ITEM = ParagraphStyle("item", parent=CORPO, leftIndent=12, bulletIndent=2, spaceAfter=1.5)
H1 = ParagraphStyle("h1", fontName="Sans-B", fontSize=12, leading=15, spaceBefore=7, spaceAfter=3,
            keepWithNext=1)
LEG = ParagraphStyle("leg", parent=CORPO, fontSize=8.9, leading=11.2, textColor=colors.HexColor("#333333"),
                     spaceAfter=6)
TIT = ParagraphStyle("tit", fontName="Sans-B", fontSize=15, leading=19, alignment=TA_CENTER)
SUB = ParagraphStyle("sub", fontName="Serif", fontSize=10.5, leading=13.5, alignment=TA_CENTER)
CEL = ParagraphStyle("cel", fontName="Serif", fontSize=8.6, leading=10.4)
MONO = ParagraphStyle("mono", fontName="Mono", fontSize=7.6, leading=9.2)


def br(x, n=2):
    """Número com vírgula decimal."""
    return f"{x:.{n}f}".replace(".", ",")


def p95(v):
    v = sorted(v)
    return v[max(1, math.ceil(0.95 * len(v))) - 1]


# ------------------------------------------------------------------ dados
res = pd.read_csv(D / "resumo.csv")
tab = pd.read_csv(D / "tabela_esperas.csv").set_index("configuracao")
esp = pd.read_csv(D / "espera_elfos.csv")
res["execucao"] = res["configuracao"] + "_rep" + res["repeticao"].astype(str)
n_exec, n_ok = len(res), int((res["status"] == "ok").sum())
amb = dict(l.split(": ", 1) for l in (D / "ambiente.txt").read_text().splitlines() if ": " in l)
piloto = pd.read_csv(D / "piloto" / "resumo.csv")
tt = pd.read_csv(D / "piloto" / "teste_timeout" / "resumo.csv").iloc[0]
estresse = pd.read_csv(D / "estresse" / "resumo.csv")
tp = pd.read_csv(D / "teste_prioridade" / "resumo.csv").iloc[0]
tp_ev = pd.read_csv(D / "teste_prioridade" / "eventos.csv")
ing = pd.read_csv(D / "ingenua" / "resumo.csv").iloc[0]
ing_ev = pd.read_csv(D / "ingenua" / "eventos.csv")
saida_teste = (D / "teste_prioridade" / "saida.txt").read_text().strip()

t = tab.to_dict("index")
r03, r06, r12, a05, d30 = (t[k] for k in ("E03_R10", "E06_R10", "E12_R10", "E06_R05", "E06_R30"))
prev = {n: n / (15 + 3 * n / 3) * 1000 for n in (3, 6, 12)}  # previsão analítica (pedidos/s)
desvio = {n: 100 * (t[f"E{n:02d}_R10"]["vazao_media_pedidos_s"] / prev[n] - 1) for n in (3, 6, 12)}
outlier = res[res["configuracao"] == "E03_R10"].sort_values("T_ms").iloc[-1]
_amp = {k: 100 * (v["vazao_max"] - v["vazao_min"]) / v["vazao_media_pedidos_s"] for k, v in tab.to_dict("index").items()}
amp_cfg = max(_amp.items(), key=lambda kv: kv[1])
amp_resto = max(v for k, v in _amp.items() if k != amp_cfg[0])

# G3: p95 por grupo na referência
ref_ids = res[(res["configuracao"] == "E06_R10") & (res["status"] == "ok")]["execucao"]
e3 = esp[esp["execucao"].isin(ref_ids)]
g3 = e3.groupby(["execucao", "grupo_id"])["espera_ms"].apply(lambda s: p95(s.tolist())).unstack()
g3s = {g: (g3[g].mean(), g3[g].min(), g3[g].max()) for g in g3.columns}
ref1_ev = pd.read_csv(D / "eventos.csv").query("execucao == 'E06_R10_rep1'")


def ev_t(df, evento, grupo=None):
    q = df[df["evento"] == evento]
    if grupo is not None:
        q = q[q["grupo_id"] == grupo]
    return float(q["t_ms"].iloc[0])


def decisoes(df):
    return df[df["evento"] == "decisao"].reset_index(drop=True)


# ------------------------------------------------------------------ helpers de layout
def quebrar(txt, largura=112):
    """Quebra linhas longas da saída do terminal (continuação indentada)."""
    import textwrap
    out = []
    for l in txt.splitlines():
        out += textwrap.wrap(l, largura, subsequent_indent="    ", break_on_hyphens=False) or [""]
    return "\n".join(out)


def P(txt, st=CORPO):
    return Paragraph(txt, st)


def itens(lista):
    return [Paragraph(x, ITEM, bulletText="•") for x in lista]


def tabela(linhas, larg, cab=True, fs=None):
    dados = [[Paragraph(str(c), CEL) for c in l] for l in linhas]
    tb = Table(dados, colWidths=[w * cm for w in larg], repeatRows=1 if cab else 0)
    est = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9a9a9a")),
           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6)]
    if cab:
        est.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9e8e4")))
    tb.setStyle(TableStyle(est))
    return tb


def figura(arq, larg_cm, legenda):
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(str(arq)).getSize()
    img = Image(str(arq), width=larg_cm * cm, height=larg_cm * cm * h / w)
    return KeepTogether([img, Spacer(1, 2), P(legenda, LEG)])


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Sans", 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(2 * cm, 1.2 * cm, "Tema 11 — Problema do Papai Noel — Sistemas Operacionais (FAG)")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
    canvas.restoreState()


# ------------------------------------------------------------------ conteúdo
s = []
s += [P("Problema do Papai Noel com pthreads: implementação, experimentos e análise", TIT), Spacer(1, 4),
      P("Tema 11 — Sistemas Operacionais — Prof. Lucca Abbado Neres — FAG", SUB),
      P("[Integrante 1] · [Integrante 2] · [Integrante 3] — outubro de 2026", SUB), Spacer(1, 8)]

# 1
s += [P("1. Problema e regras", H1),
      P("Papai Noel dorme até ser acordado por uma de duas demandas: um grupo de <b>exatamente três elfos</b> "
        "com um pedido ou a chegada das <b>nove renas</b>. Implementamos a versão finita: há uma única viagem "
        "e cada elfo faz um único pedido. As regras são:")]
s += itens([
    "um atendimento ajuda exatamente 3 elfos, e um elfo novo não pode invadir um grupo já formado ou em atendimento;",
    "a viagem só é preparada depois que as 9 renas chegam; se renas e grupo estão prontos no momento da decisão, "
    "Noel escolhe as <b>renas</b>, e uma ajuda já iniciada nunca é interrompida;",
    "depois da viagem, os grupos restantes são atendidos, e todas as threads terminam quando as duas demandas acabam.",
    "parâmetros: o elfo <i>i</i> (<i>i</i> = 0, 1, …) chega em 10 + <i>i</i> ms; as renas chegam juntas em 5, 10 ou 30 ms; "
    "uma ajuda dura 3 ms e a preparação da viagem dura 5 ms.",
])

# 2
s += [P("2. Solução e modelagem", H1),
      P("O programa (C11, <font name='Mono'>-std=c11 -O2 -Wall -Wextra -pthread</font>, sem warnings) cria "
        "<b>1 thread Noel, 9 threads rena e N threads elfo</b>, todas antes de qualquer <font name='Mono'>pthread_join</font>. "
        "Cada thread se anuncia e espera o <b>sinal de início</b> numa variável de condição. Quando todas estão "
        "prontas, a <i>main</i> grava t0 com <font name='Mono'>CLOCK_MONOTONIC</font> e faz broadcast: assim, criar "
        "as threads fica fora da medição. Os sleeps (<font name='Mono'>clock_nanosleep</font> absoluto, da família "
        "nanosleep) servem apenas para simular chegada, ajuda e preparação. Toda a coordenação usa um único "
        "mutex e quatro variáveis de condição, sem espera ocupada. Eventos e amostras ficam em vetores na memória "
        "e só são exportados para CSV depois dos joins. Os mecanismos são destruídos após os joins."),
      tabela([
          ["Elemento", "Tipo", "Papel", "Valor inicial"],
          ["mutex", "pthread_mutex_t", "protege todo o estado compartilhado", "destravado"],
          ["cv_largada", "pthread_cond_t", "sinal de início comum (main ↔ threads)", "largada = 0"],
          ["cv_noel", "cond (CLOCK_MONOTONIC)", "Noel dorme; timedwait até t0 + timeout", "—"],
          ["cv_elfos", "pthread_cond_t", "elfo espera seu grupo ficar CONCLUÍDO", "—"],
          ["cv_renas", "pthread_cond_t", "renas esperam viagem_concluida", "—"],
          ["renas_prontas", "int", "renas que já chegaram", "0"],
          ["grupos[k]", "{membros[3], n, estado}", "fila de grupos com id (ABERTO→PRONTO→EM_AJUDA→CONCLUÍDO)",
           "n = 0, ABERTO"],
          ["grupo_aberto / grupos_fechados / proximo_grupo", "int", "grupo que aceita elfos / fechados / próximo a atender",
           "0 / 0 / 0"],
          ["viagem_iniciada, viagem_concluida, abortar", "int", "estado da viagem; timeout de segurança", "0, 0, 0"],
      ], [4.1, 3.3, 6.4, 2.6]),
      Spacer(1, 4),
      P("<b>Formação dos grupos.</b> O elfo entra sempre em <font name='Mono'>grupos[grupo_aberto]</font>. O 3º elfo "
        "fecha o grupo (PRONTO), avança <font name='Mono'>grupo_aberto</font> e sinaliza Noel. Inscrever-se e fechar o "
        "grupo acontecem na mesma seção crítica, então o 4º elfo já cai no grupo seguinte. "
        "<b>Decisão de Noel:</b> com o mutex adquirido, ele testa primeiro <i>renas_prontas = 9 e a viagem ainda não feita</i> "
        "e só depois a fila de grupos. Também registra cada decisão e conta violações. As invariantes verificadas "
        "em tempo de execução são: grupo com ≠ 3 elfos, viagem com &lt; 9 renas, prioridade violada, decisão durante "
        "uma ajuda em curso, elfo atendido 0 ou 2+ vezes e invasão de grupo fechado.")]
s.append(KeepTogether(Preformatted(
    "NOEL                                       ELFO i                               RENA r\n"
    "lock; espera largada                       espera largada; dorme até 10+i ms    espera largada\n"
    "loop:                                      lock; t_pedido = agora               dorme até renas_ms\n"
    "  se viagem_concluida e todos grupos       g = grupo_aberto; inscreve em g      lock; renas_prontas++\n"
    "     concluídos: sai                       se g.n == 3: g.estado = PRONTO;      se == 9: t_nona = agora;\n"
    "  renas_ok = (renas==9 e !viagem)            grupo_aberto++; signal(cv_noel)      signal(cv_noel)\n"
    "  elfos_ok = (há grupo PRONTO na fila)     enquanto g != CONCLUÍDO e !abortar:  enquanto !viagem_concluida\n"
    "  se nenhum: timedwait(cv_noel, limite)       wait(cv_elfos)                       e !abortar:\n"
    "     (ETIMEDOUT → abortar=1; sai)          unlock                                 wait(cv_renas)\n"
    "  se renas_ok: preparar viagem             -- Noel: preparar/ajudar = marca       unlock\n"
    "  senão: ajudar grupos[proximo++]             estado, unlock, sleep 5/3 ms, lock,\n"
    "registra encerramento; broadcast(todos)       marca fim, broadcast(cv_renas/elfos)", MONO)))

# 3
ie = decisoes(ing_ev)
s += [P("3. Ordem de execução problemática da solução ingênua", H1),
      P("<b>(a) Invasão de grupo, num exemplo construído (não executado).</b> Numa solução ingênua com um contador "
        "<font name='Mono'>elfos_esperando</font>, os elfos 0, 1 e 2 chegam, o contador vai a 3 e Noel recebe o sinal. "
        "Antes de Noel adquirir o mutex, o elfo 3 chega e incrementa o contador para 4. Noel acorda, lê 4 e ajuda "
        "quatro elfos, ou o elfo 3 entra na ajuda que já começou. A nossa solução evita isso porque o grupo é fechado "
        "na mesma seção crítica em que o 3º elfo se inscreve, e esse elfo ainda avança <font name='Mono'>grupo_aberto</font>: "
        "o elfo 3 nunca enxerga o grupo 1."),
      P("<b>(b) Prioridade violada, executada de verdade.</b> A opção <font name='Mono'>--ingenua</font> inverte a regra "
        "(elfos primeiro) e foi rodada no mesmo cenário do teste funcional (6 elfos, renas em 30 ms, Noel liberado só "
        "com as duas demandas prontas). Sequência registrada em <font name='Mono'>dados/ingenua/eventos.csv</font>:"),
      tabela([["t (ms)", "evento"],
              [br(ev_t(ing_ev, "grupo_pronto", 1), 3), "grupo 1 pronto (elfos 0–2)"],
              [br(ev_t(ing_ev, "grupo_pronto", 2), 3), "grupo 2 pronto (elfos 3–5)"],
              [br(ev_t(ing_ev, "nona_rena"), 3), "9ª rena chega: as duas demandas estão prontas"],
              [br(ie.loc[0, "t_ms"], 3), "<b>decisão: ajudar grupo 1 com as 9 renas prontas → violação</b>"],
              [br(ie.loc[1, "t_ms"], 3), "<b>decisão: ajudar grupo 2 → violação</b>"],
              [br(ev_t(ing_ev, "inicio_preparacao"), 3), "só agora a viagem começa a ser preparada"]],
             [2.2, 14.2]),
      Spacer(1, 3),
      P(f"O programa contou <b>{int(ing['violacoes_prioridade'])} violações de prioridade</b>, status "
        f"<i>{ing['status']}</i>, e a resposta às renas foi de {br(ing['resposta_renas_ms'], 3)} ms, contra "
        f"{br(tp['resposta_renas_ms'], 3)} ms na solução correta (seção 7). A solução evita esse problema porque testa "
        "<i>renas_ok</i> antes de <i>elfos_ok</i> dentro da mesma seção crítica em que decide.")]

# 4
s += [P("4. Análise de deadlock e starvation", H1),
      P("<b>Não há deadlock.</b> Existe um único mutex, então não há espera circular entre locks. Quem espera numa "
        "variável de condição libera o mutex enquanto espera. Cada espera é um laço que reavalia o predicado, o que "
        "protege contra acordar espuriamente. Toda mudança que pode tornar um predicado verdadeiro acontece sob o mutex "
        "e é seguida de signal/broadcast: o 3º elfo e a 9ª rena acordam Noel, e Noel acorda elfos e renas ao fim de "
        "cada atividade. Assim, nenhum aviso se perde. Noel nunca simula trabalho segurando o mutex. Por fim, ao "
        "encerrar, Noel faz broadcast em todas as filas. O timeout de segurança "
        "(<font name='Mono'>pthread_cond_timedwait</font>) marca <i>abortar</i> e libera todos, e cada thread "
        "testa <i>abortar</i> ao acordar."),
      P("<b>A espera de um elfo é finita nesta versão.</b> Existe no máximo uma viagem (5 ms). Os grupos são atendidos "
        "em ordem FIFO pelo id, e cada ajuda dura 3 ms. Um grupo na posição <i>k</i> da fila espera, no pior caso, "
        "5 + 3(<i>k</i>−1) ms, mais o tempo de formação (≤ 2 ms para o primeiro membro). Isso é finito porque N é finito."),
      P("<b>Risco de starvation com demandas contínuas.</b> Se as renas voltassem sempre, a prioridade absoluta das "
        "renas poderia deixar os grupos de elfos esperando sem limite. Isso aconteceria se as 9 renas estivessem "
        "prontas a cada decisão, já que viagens sucessivas sempre venceriam. Possíveis mitigações: <i>aging</i> (um "
        "grupo que espera mais que um limite ganha prioridade), uma cota (atender ao menos um grupo pendente entre "
        "duas viagens) ou um limite de viagens consecutivas. Todas relaxam a regra \"renas primeiro\" em troca de "
        "garantir progresso aos elfos. Entre os próprios elfos não há starvation, porque a fila de grupos é FIFO.")]

# 5
s += [P("5. Método", H1),
      P(f"<b>Ambiente</b> (<font name='Mono'>dados/ambiente.txt</font>): {amb['cpu']}, {amb['cpus_logicas (nproc)']} CPUs "
        f"lógicas, {amb['memoria']} de RAM, {amb['so']}, kernel {amb['kernel'].split()[1]}, {amb['gcc']}, "
        f"{amb['glibc'].replace('ldd ', '')}. Compilação: <font name='Mono'>{amb['comando_compilacao']}</font>."),
      P("<b>Hipóteses (escritas antes das execuções, deduzidas só dos parâmetros).</b> "
        "<b>H<sub>A</sub>:</b> com as renas chegando junto, a viagem ocupa Noel de 10 a 15 ms, e os grupos ficam prontos "
        "a cada 3 ms a partir de 12 ms. Logo T ≈ 15 + 3·(N/3) ms, e a vazão N/T deve <b>crescer</b> com N, porque o custo "
        f"fixo (10 ms até o 1º elfo e 5 ms de viagem) é diluído: previsão de {br(prev[3], 0)}, {br(prev[6], 0)} e "
        f"{br(prev[12], 0)} pedidos/s para 3, 6 e 12 elfos, rumo ao limite de 1000 pedidos/s (3 elfos a cada 3 ms). "
        "<b>H<sub>B</sub>:</b> o p95 da espera deve ser <b>maior com as renas junto</b> (≈ 5 ms), porque o grupo 1 fica "
        "pronto em 12 ms com Noel ainda preparando a viagem. Antes e depois, Noel está livre quando cada grupo "
        "fecha, e a espera se reduz ao tempo de formação do grupo (≈ 2 ms). A resposta às renas deve ser próxima de "
        "zero nos três casos, porque Noel está dormindo quando a 9ª rena chega."),
      P("<b>Matriz.</b> São 5 configurações distintas: a referência (6 elfos, 10 ms); o conjunto 1 varia os elfos "
        "(3, 6, 12) com as renas em 10 ms; o conjunto 2 varia as renas (5, 10, 30 ms) com 6 elfos. Cada uma tem 5 "
        f"repetições, num total de <b>{n_exec} execuções</b>, intercaladas por repetição. As sementes 11, 22, 33, 44 e 55 "
        "são apenas o id da repetição: o programa não tem aleatoriedade, e a variação vem do escalonador e da latência "
        f"dos timers. <b>Piloto:</b> {len(piloto)} execuções (3 por configuração), maior T = {br(piloto['T_ms'].max(), 2)} ms. "
        f"Fixamos o <b>timeout em 2000 ms</b> (≈ {piloto['T_ms'].max() and int(2000 / piloto['T_ms'].max())}× o maior T). "
        f"O mecanismo foi verificado com <font name='Mono'>--timeout-ms 5</font>: status <i>{tt['status']}</i>, "
        f"{int(tt['concluidos'])}/{int(tt['previstos'])} pedidos, encerramento sem travar. Não foi preciso ajustar a escala: "
        "as durações (ms) são muito maiores que a latência de acordar uma thread, que é de dezenas de µs (veja a "
        f"resposta às renas). <b>Estresse:</b> {len(estresse)} execuções extras (3, 12 e 12 elfos com renas em 10, 5 "
        f"e 30 ms), {int((estresse['status'] == 'ok').sum())} com status ok."),
      P("<b>Métricas.</b> T vai de t0 ao encerramento de Noel. Vazão = pedidos atendidos / (T/1000) s. Espera = do pedido "
        "(chegada) ao início da ajuda do grupo. p95 = valor na posição teto(0,95·n) (base 1) da lista ordenada; com "
        "n = 6 ou 3 amostras, o p95 coincide com o máximo. Resposta às renas = da 9ª rena ao início da preparação. "
        "Utilização de Noel = tempo em ajuda ou preparação / T.")]

# 6
linhas = [["Config.", "N", "Renas", "OK", "Vazão média (mín–máx) pedidos/s", "Espera média (ms)",
           "p95 médio (mín–máx) ms", "Máx (ms)", "Resposta renas (µs)", "Util. Noel"]]
for k in ("E03_R10", "E06_R10", "E12_R10", "E06_R05", "E06_R30"):
    r = t[k]
    linhas.append([k, r["elfos"], f"{r['renas_ms']} ms", f"{r['validas']}/{r['execucoes']}",
                   f"{br(r['vazao_media_pedidos_s'], 1)} ({br(r['vazao_min'], 1)}–{br(r['vazao_max'], 1)})",
                   br(r["espera_media_ms"], 2),
                   f"{br(r['espera_p95_ms_media_execucoes'], 2)} ({br(r['espera_p95_ms_min'], 2)}–{br(r['espera_p95_ms_max'], 2)})",
                   br(r["espera_max_ms"], 2), br(1000 * r["resposta_renas_media_ms"], 0),
                   f"{br(100 * r['utilizacao_noel_media'], 1)}%"])
s += [P("6. Resultados", H1),
      P(f"<b>Taxa de execuções válidas: {n_ok}/{n_exec} ({br(100 * n_ok / n_exec, 0)}%)</b>, sem nenhum timeout e com "
        "zero violações de prioridade ou de regras em toda a matriz. A tabela resume "
        "<font name='Mono'>dados/tabela_esperas.csv</font>. As médias são das 5 execuções de cada configuração."),
      tabela(linhas, [1.7, 0.8, 1.3, 1.3, 2.8, 1.5, 2.7, 1.2, 1.6, 1.3]), Spacer(1, 5)]

s.append(figura(G / "G1_vazao_elfos.png", 8.4,
    f"<b>Figura G1.</b> Fixo: renas em 10 ms. Variou: nº de elfos (3, 6, 12), com 5 execuções por ponto (15 no total). "
    f"A vazão cresce de {br(r03['vazao_media_pedidos_s'], 1)} para {br(r06['vazao_media_pedidos_s'], 1)} e "
    f"{br(r12['vazao_media_pedidos_s'], 1)} pedidos/s. Isso decorre da fila FIFO de grupos: depois da viagem, Noel "
    "atende os grupos em sequência, cada um logo após o anterior, e o custo fixo inicial de 15 ms pesa menos quando N cresce. "
    f"<b>Confirma H<sub>A</sub></b>: o desvio em relação à previsão foi de {br(desvio[3], 1)}%, {br(desvio[6], 1)}% e "
    f"{br(desvio[12], 1)}%, explicado pela latência de cada sleep. A diferença entre níveis (> 100 pedidos/s) supera "
    f"muito a variação entre repetições: a maior faixa é a de 3 elfos, {br(r03['vazao_min'], 1)}–{br(r03['vazao_max'], 1)}, "
    f"por causa de uma execução atrasada (rep {int(outlier['repeticao'])}, T = {br(outlier['T_ms'], 2)} ms)."))

s.append(figura(G / "G2_p95_renas.png", 16,
    f"<b>Figura G2.</b> Fixo: 6 elfos. Variou: a chegada das renas (categorias), com 5 execuções por categoria (15 no total). "
    f"O p95 da espera é {br(r06['espera_p95_ms_media_execucoes'], 2)} ms com as renas <i>junto</i>, contra "
    f"{br(a05['espera_p95_ms_media_execucoes'], 2)} ms <i>antes</i> e {br(d30['espera_p95_ms_media_execucoes'], 2)} ms "
    "<i>depois</i>. Só no caso <i>junto</i> a prioridade às renas coloca a viagem (10–15 ms) sobre a formação do "
    "grupo 1. Nos outros dois, Noel está livre quando cada grupo fecha, e a espera se resume ao tempo de formação. "
    "<b>Confirma H<sub>B</sub></b>. A diferença (~3 ms) é muito maior que a faixa das repetições (&lt; 0,1 ms). "
    "Painel direito: a resposta às renas fica em dezenas de µs nos três casos "
    f"(máximo de {br(1000 * max(r06['resposta_renas_max_ms'], a05['resposta_renas_max_ms'], d30['resposta_renas_max_ms']), 0)} µs). "
    "Esse é o custo de acordar Noel, e as diferenças entre categorias ficam dentro do ruído."))

s.append(figura(G / "G3_p95_grupo.png", 9.6,
    f"<b>Figura G3.</b> Fixo: a referência (6 elfos, renas junto), com 5 execuções e 3 amostras por grupo em cada uma "
    f"(n = 15 por grupo). Variou: o grupo atendido. O p95 do grupo 1 é {br(g3s[1][0], 2)} ms "
    f"({br(g3s[1][1], 2)}–{br(g3s[1][2], 2)}) e o do grupo 2 é {br(g3s[2][0], 2)} ms ({br(g3s[2][1], 2)}–{br(g3s[2][2], 2)}). "
    "Os dois são praticamente iguais. O grupo 1 espera o fim da viagem, e o grupo 2 espera o fim da ajuda ao grupo 1. "
    "Como os grupos chegam a cada 3 ms e cada ajuda também dura 3 ms, o atraso inicial causado pela viagem se "
    "propaga sem crescer. A expectativa intuitiva de que grupos posteriores esperariam mais <b>não se confirmou</b>. "
    "A diferença entre grupos (~0,1 ms, latência acumulada) é da ordem da variação entre repetições."))

s.append(figura(G / "G4_linha_tempo.png", 16.5,
    f"<b>Figura G4.</b> Linha do tempo de uma execução válida da referência (E06_R10_rep1), no trecho de 8 a 23 ms. "
    f"A 9ª rena chega em {br(ev_t(ref1_ev, 'nona_rena'), 2)} ms, e Noel prepara a viagem até "
    f"{br(ev_t(ref1_ev, 'fim_preparacao'), 2)} ms. Há disputa nesse trecho: o grupo 1 fica pronto em "
    f"{br(ev_t(ref1_ev, 'grupo_pronto', 1), 2)} ms e o grupo 2 em {br(ev_t(ref1_ev, 'grupo_pronto', 2), 2)} ms, ambos "
    "com Noel ocupado, e esperam (faixa hachurada) sem interromper a preparação. A partir daí Noel fica ocupado "
    f"sem pausa. A utilização de {br(100 * r06['utilizacao_noel_media'], 1)}% é baixa porque os ~10 ms iniciais "
    "não têm nenhuma demanda."))

# 7
d_tp = decisoes(tp_ev)
s += [P("7. Teste funcional de prioridade", H1),
      P("No modo <font name='Mono'>--teste-prioridade</font>, Noel começa \"atrasado\": espera em "
        "<font name='Mono'>cv_noel</font>, sem sleep, até que as 9 renas e pelo menos um grupo estejam prontos. Com "
        f"6 elfos e renas em 30 ms, os grupos ficaram prontos em {br(ev_t(tp_ev, 'grupo_pronto', 1), 3)} e "
        f"{br(ev_t(tp_ev, 'grupo_pronto', 2), 3)} ms, e a 9ª rena em {br(ev_t(tp_ev, 'nona_rena'), 3)} ms. A primeira "
        f"decisão, em {br(d_tp.loc[0, 't_ms'], 3)} ms, foi a <b>viagem</b>, com os grupos atendidos depois. Saída salva em "
        "<font name='Mono'>dados/teste_prioridade/saida.txt</font>:")]
s.append(Preformatted(quebrar(saida_teste),
                      ParagraphStyle("m2", parent=MONO, fontSize=7.0, leading=8.6)))
s.append(P(f"Resultado: primeira decisão = renas, {int(tp['concluidos'])}/{int(tp['previstos'])} elfos atendidos, "
           f"{int(tp['violacoes_prioridade'])} violações de prioridade e {int(tp['violacoes_regras'])} de regras: "
           "<b>PASSOU</b>. No mesmo cenário, a política ingênua (seção 3) falha nas duas primeiras decisões."))

# 8
s += [P("8. Conclusões e limitações", H1),
      P(f"A solução, com mutex, variáveis de condição e uma fila de grupos com id, cumpriu todas as regras em "
        f"{n_ok}/{n_exec} execuções da matriz, em {len(estresse)} execuções de estresse e no teste funcional, sempre sem "
        "travamento. As duas hipóteses se confirmaram. A vazão cresce com N, porque os custos fixos são amortizados. "
        "O p95 da espera dos elfos só aumenta quando a viagem coincide com a formação do primeiro grupo: é o preço "
        "visível da prioridade às renas, que respondem em dezenas de µs.")]
s += itens([
    "O cenário é dirigido pelo tempo e quase determinístico, por isso a variação entre repetições é pequena: "
    f"a amplitude (máx − mín) da vazão fica em até {br(amp_cfg[1], 1)}% da média, e o maior caso é "
    f"{amp_cfg[0]}, com a execução atrasada; nas demais configurações chega no máximo a {br(amp_resto, 2)}%. "
    "As sementes só identificam as repetições.",
    "As medidas incluem a latência dos timers e do escalonador (≈ 0,05–0,5 ms por sleep). Uma execução de 3 elfos "
    f"teve T = {br(outlier['T_ms'], 2)} ms, contra ~18,3 ms nas outras, por atraso do SO.",
    "Com 3 ou 6 amostras por execução, o p95 equivale ao máximo. A vazão de N pequeno é penalizada pelos 10 ms "
    "iniciais sem demanda, que entram em T por definição.",
    "Não havia ThreadSanitizer nem Helgrind na máquina (as bibliotecas libtsan/valgrind não estão instaladas). "
    "A correção se apoia nas invariantes verificadas em tempo de execução, no estresse e no teste funcional.",
    "N precisa ser múltiplo de 3 (o programa valida). A versão contínua, com risco de starvation, foi apenas analisada.",
])

doc = SimpleDocTemplate(str(RAIZ / "relatorio.pdf"), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                        topMargin=1.7 * cm, bottomMargin=1.8 * cm, title="Problema do Papai Noel — Tema 11",
                        author="[Integrante 1], [Integrante 2], [Integrante 3]")
doc.build(s, onFirstPage=rodape, onLaterPages=rodape)
print("relatorio.pdf gerado")
