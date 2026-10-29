#!/usr/bin/env python3
"""graficos.py — gera G1..G4 e tabela_esperas.csv a partir SOMENTE dos CSVs.

Uso (a partir de qualquer pasta):
    python3 scripts/graficos.py [--dados dados] [--saida graficos]

Lê dados/resumo.csv, dados/espera_elfos.csv e dados/eventos.csv (as 25
execuções da matriz) e grava PNGs a 200 dpi em graficos/ e a tabela em
dados/tabela_esperas.csv.
"""
import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

# Paleta (slots categóricos validados) e tintas de texto.
AZUL, LARANJA, AQUA, VIOLETA = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
CINZA = "#c9c8c3"
TXT, TXT2 = "#0b0b0b", "#52514e"
DPI = 200

plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 12.5, "axes.labelsize": 11,
    "axes.edgecolor": TXT2, "axes.labelcolor": TXT, "xtick.color": TXT2,
    "ytick.color": TXT2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8,
    "axes.axisbelow": True, "legend.frameon": False, "figure.dpi": 100,
})

ROTULO_RENAS = {5: "antes\n(5 ms)", 10: "junto\n(10 ms)", 30: "depois\n(30 ms)"}


def p95(valores):
    """Posição ceil(0,95·n), base 1, nos valores ordenados."""
    v = sorted(valores)
    if not v:
        return float("nan")
    return v[max(1, math.ceil(0.95 * len(v))) - 1]


def resumir(df, col):
    g = df.groupby(col)
    return pd.DataFrame({"media": g.mean(), "min": g.min(), "max": g.max(), "n": g.count()})


def barras_minmax(ax, x, s, cor, rotulo):
    err = [s["media"] - s["min"], s["max"] - s["media"]]
    ax.errorbar(x, s["media"], yerr=err, fmt="o", ms=8, color=cor, ecolor=cor,
                elinewidth=2, capsize=6, capthick=2, label=rotulo, zorder=3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default=str(RAIZ / "dados"))
    ap.add_argument("--saida", default=str(RAIZ / "graficos"))
    a = ap.parse_args()
    dados, saida = Path(a.dados), Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)

    res = pd.read_csv(dados / "resumo.csv")
    esp = pd.read_csv(dados / "espera_elfos.csv")
    eve = pd.read_csv(dados / "eventos.csv")
    res["execucao"] = res["configuracao"] + "_rep" + res["repeticao"].astype(str)
    validas = res[res["status"] == "ok"].copy()

    # ---------- tabela de esperas por configuração ----------
    linhas = []
    for cfg, d in res.groupby("configuracao", sort=False):
        ok = d[d["status"] == "ok"]
        amostras = esp[esp["execucao"].isin(ok["execucao"])]["espera_ms"].dropna()
        linhas.append({
            "configuracao": cfg, "conjunto": d["conjunto"].iloc[0],
            "elfos": int(d["elfos"].iloc[0]), "renas_ms": int(d["renas_ms"].iloc[0]),
            "execucoes": len(d), "validas": len(ok),
            "taxa_validas": round(len(ok) / len(d), 3),
            "espera_media_ms": round(ok["espera_media_ms"].mean(), 3),
            "espera_p95_ms_media_execucoes": round(ok["espera_p95_ms"].mean(), 3),
            "espera_p95_ms_min": round(ok["espera_p95_ms"].min(), 3),
            "espera_p95_ms_max": round(ok["espera_p95_ms"].max(), 3),
            "espera_p95_ms_amostras_agrupadas": round(p95(amostras.tolist()), 3),
            "espera_max_ms": round(ok["espera_max_ms"].max(), 3),
            "n_amostras_total": int(ok["n_amostras"].sum()),
            "vazao_media_pedidos_s": round(ok["vazao_pedidos_s"].mean(), 2),
            "vazao_min": round(ok["vazao_pedidos_s"].min(), 2),
            "vazao_max": round(ok["vazao_pedidos_s"].max(), 2),
            "T_medio_ms": round(ok["T_ms"].mean(), 3),
            "resposta_renas_media_ms": round(ok["resposta_renas_ms"].mean(), 4),
            "resposta_renas_max_ms": round(ok["resposta_renas_ms"].max(), 4),
            "utilizacao_noel_media": round(ok["utilizacao_noel"].mean(), 4),
            "violacoes_prioridade": int(d["violacoes_prioridade"].sum()),
            "violacoes_regras": int(d["violacoes_regras"].sum()),
        })
    tab = pd.DataFrame(linhas).sort_values(["elfos", "renas_ms"])
    tab.to_csv(dados / "tabela_esperas.csv", index=False)
    taxa = len(validas) / len(res)
    print(f"execuções válidas: {len(validas)}/{len(res)} ({100 * taxa:.0f}%)")
    print(tab.to_string(index=False))

    # ---------- G1: elfos x vazão (renas junto) ----------
    c1 = validas[validas["renas_ms"] == 10]
    s1 = resumir(c1.set_index("elfos")["vazao_pedidos_s"], "elfos").sort_index()
    fig, ax = plt.subplots(figsize=(7, 4.6))
    barras_minmax(ax, s1.index, s1, AZUL, "média de 5 repetições (barra = mín–máx)")
    ax.plot(s1.index, s1["media"], color=AZUL, lw=2, alpha=0.5, zorder=2)
    for x, r in s1.iterrows():
        ax.annotate(f"{r['media']:.1f}", (x, r["media"]), textcoords="offset points",
                    xytext=(10, -14), color=TXT, fontsize=10)
    ax.set_xticks([3, 6, 12])
    ax.set_xlabel("Quantidade de elfos (fator A)")
    ax.set_ylabel("Vazão (pedidos de elfos atendidos / s)")
    ax.set_ylim(0, s1["max"].max() * 1.18)
    ax.set_title(f"G1 — Vazão × nº de elfos (renas junto, 10 ms; n = {int(s1['n'].min())} execuções por ponto)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(saida / "G1_vazao_elfos.png", dpi=DPI)
    plt.close(fig)

    # ---------- G2: chegada das renas x p95 (6 elfos) + resposta às renas ----------
    c2 = validas[validas["elfos"] == 6]
    ordem = [5, 10, 30]
    s2 = resumir(c2.set_index("renas_ms")["espera_p95_ms"], "renas_ms").reindex(ordem)
    s2r = resumir(c2.set_index("renas_ms")["resposta_renas_ms"] * 1000, "renas_ms").reindex(ordem)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw={"width_ratios": [1.35, 1]})
    xs = range(len(ordem))
    barras_minmax(ax, list(xs), s2, LARANJA, "média dos 5 p95 (barra = mín–máx)")
    for i, (_, r) in enumerate(s2.iterrows()):
        ax.annotate(f"{r['media']:.2f} ms", (i, r["media"]), textcoords="offset points",
                    xytext=(12, -4), color=TXT, fontsize=10)
    ax.set_xticks(list(xs), [ROTULO_RENAS[r] for r in ordem])
    ax.set_xlim(-0.5, 2.7)
    ax.set_ylim(0, s2["max"].max() * 1.3)
    ax.set_xlabel("Chegada das 9 renas (fator B)")
    ax.set_ylabel("p95 da espera dos elfos (ms)")
    ax.set_title("p95 da espera dos elfos (6 elfos)")
    ax.legend(loc="upper left")
    barras_minmax(ax2, list(xs), s2r, VIOLETA, "média de 5 (barra = mín–máx)")
    for i, (_, r) in enumerate(s2r.iterrows()):
        ax2.annotate(f"{r['media']:.0f} µs", (i, r["media"]), textcoords="offset points",
                     xytext=(12, -4), color=TXT, fontsize=10)
    ax2.set_xticks(list(xs), [ROTULO_RENAS[r] for r in ordem])
    ax2.set_xlim(-0.5, 2.7)
    ax2.set_ylim(0, s2r["max"].max() * 1.4)
    ax2.set_xlabel("Chegada das 9 renas (fator B)")
    ax2.set_ylabel("Resposta às renas (µs)")
    ax2.set_title("Tempo de resposta às renas\n(9ª rena → início da preparação)")
    ax2.legend(loc="upper left")
    fig.suptitle(f"G2 — Efeito da chegada das renas (6 elfos; n = {int(s2['n'].min())} execuções por categoria)",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(saida / "G2_p95_renas.png", dpi=DPI)
    plt.close(fig)

    # ---------- G3: referência, p95 por grupo ----------
    ref_exec = validas[(validas["elfos"] == 6) & (validas["renas_ms"] == 10)]["execucao"]
    e3 = esp[esp["execucao"].isin(ref_exec)].dropna(subset=["espera_ms"])
    por = e3.groupby(["execucao", "grupo_id"])["espera_ms"].agg(p95=lambda s: p95(s.tolist()), n="count")
    por = por.reset_index()
    s3 = por.groupby("grupo_id")["p95"].agg(media="mean", min="min", max="max", n="count")
    namostra = por.groupby("grupo_id")["n"].sum()
    fig, ax = plt.subplots(figsize=(7, 4.6))
    barras_minmax(ax, s3.index, s3, AQUA, "média dos 5 p95 (barra = mín–máx)")
    ax.scatter(por["grupo_id"] + 0.12, por["p95"], s=22, color=TXT2, zorder=4,
               label="p95 de cada execução")
    for g, r in s3.iterrows():
        ax.annotate(f"{r['media']:.2f} ms\n{int(r['n'])} execuções × 3 elfos\n(n = {int(namostra[g])} amostras)",
                    (g, r["min"]), textcoords="offset points", xytext=(0, -54), ha="center",
                    color=TXT, fontsize=9.5)
    ax.set_xticks(list(s3.index), [f"grupo {int(g)}" for g in s3.index])
    ax.set_xlim(0.4, s3.index.max() + 0.6)
    ax.set_ylim(0, s3["max"].max() * 1.35)
    ax.set_xlabel("Grupo de elfos atendido (ordem de atendimento)")
    ax.set_ylabel("p95 da espera dos membros (ms)")
    ax.set_title("G3 — p95 da espera por grupo na referência (6 elfos, renas junto)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(saida / "G3_p95_grupo.png", dpi=DPI)
    plt.close(fig)

    # ---------- G4: linha temporal do estado de Noel ----------
    alvo = "E06_R10_rep1"
    ev = eve[eve["execucao"] == alvo].sort_values("t_ms")
    T = float(res.loc[res["execucao"] == alvo, "T_ms"].iloc[0])

    def intervalos(ini, fim):
        a = ev[ev["evento"] == ini].reset_index(drop=True)
        b = ev[ev["evento"] == fim].reset_index(drop=True)
        return [(float(x.t_ms), float(y.t_ms), x.grupo_id) for x, y in zip(a.itertuples(), b.itertuples())]

    prep = intervalos("inicio_preparacao", "fim_preparacao")
    ajudas = intervalos("inicio_ajuda", "fim_ajuda")
    prontos = ev[ev["evento"] == "grupo_pronto"]
    nona = float(ev[ev["evento"] == "nona_rena"]["t_ms"].iloc[0])
    chegadas_elfos = ev[(ev["tipo"] == "elfo") & (ev["evento"] == "chegada")]

    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.grid(axis="y", visible=False)
    y_noel, y_g = 3, {1: 2, 2: 1}
    ax.broken_barh([(0, T)], (y_noel - 0.35, 0.7), facecolors=CINZA, label="dormindo / esperando")
    for a_, b_, _ in prep:
        ax.broken_barh([(a_, b_ - a_)], (y_noel - 0.35, 0.7), facecolors=LARANJA,
                       edgecolor="white", lw=2, label="preparando viagem (5 ms)")
    for a_, b_, g in ajudas:
        ax.broken_barh([(a_, b_ - a_)], (y_noel - 0.35, 0.7), facecolors=AZUL,
                       edgecolor="white", lw=2, label="ajudando grupo k (3 ms)")
        ax.text((a_ + b_) / 2, y_noel, f"grupo {int(g)}", ha="center", va="center", color="white",
                fontsize=10, fontweight="bold")
    ax.text(sum(prep[0][:2]) / 2, y_noel, "viagem", ha="center", va="center", color="white",
            fontsize=10, fontweight="bold")
    # faixas dos grupos: espera (grupo pronto -> início) e atendimento
    for _, r in prontos.iterrows():
        g = int(r["grupo_id"])
        ini = next(a_ for a_, _, gg in ajudas if int(gg) == g)
        fim = next(b_ for _, b_, gg in ajudas if int(gg) == g)
        ax.broken_barh([(r["t_ms"], ini - r["t_ms"])], (y_g[g] - 0.25, 0.5), facecolors="none",
                       edgecolor=AQUA, hatch="///", lw=1.5, label="grupo pronto esperando Noel")
        ax.broken_barh([(ini, fim - ini)], (y_g[g] - 0.25, 0.5), facecolors=AZUL, alpha=0.55,
                       edgecolor="white", lw=2)
        ax.axvline(r["t_ms"], color=AQUA, lw=1.5, ls="--")
        ax.annotate(f"grupo {g} pronto\n{r['t_ms']:.2f} ms", (r["t_ms"], 3.62), ha="center",
                    fontsize=9, color=TXT, bbox=dict(fc="white", ec="none", pad=1))
    ax.axvline(nona, color=VIOLETA, lw=2, ls="-", label="9ª rena chega")
    ax.annotate(f"9ª rena\n{nona:.2f} ms", (nona, 3.62), ha="center", fontsize=9, color=TXT,
                bbox=dict(fc="white", ec="none", pad=1))
    for _, r in chegadas_elfos.iterrows():
        ax.plot([r["t_ms"]] * 2, [y_g[int(r["grupo_id"])] - 0.42, y_g[int(r["grupo_id"])] - 0.28],
                color=TXT2, lw=1.5)
    ax.set_yticks([y_noel, 2, 1], ["Noel", "grupo 1\n(elfos 0–2)", "grupo 2\n(elfos 3–5)"])
    x0, x1 = 8.0, math.ceil(T) + 1
    ax.set_xlim(x0, x1)
    ax.set_ylim(0.4, 4.3)
    ax.set_xlabel("Tempo desde o sinal de início (ms)")
    h, l_ = ax.get_legend_handles_labels()
    uniq = dict(zip(l_, h))
    ax.legend(uniq.values(), uniq.keys(), loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=5,
              fontsize=9.5)
    ax.set_title(f"G4 — Estado de Noel na execução {alvo} (referência: 6 elfos, renas junto)\n"
                 f"trecho mostrado: {x0:.0f}–{x1:.0f} ms de T = {T:.2f} ms; antes de 8 ms Noel só dorme; "
                 f"traços = chegada de cada elfo", fontsize=11.5)
    fig.tight_layout()
    fig.savefig(saida / "G4_linha_tempo.png", dpi=DPI)
    plt.close(fig)
    print("gráficos gravados em", saida)


if __name__ == "__main__":
    main()
