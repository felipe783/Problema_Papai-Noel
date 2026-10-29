#!/usr/bin/env bash
# run_experimentos.sh — compila e roda tudo do Tema 11 (Papai Noel).
#
# Etapas:
#   1. registra o ambiente em dados/ambiente.txt e compila (sem warnings);
#   2. piloto: 3 execuções de cada configuração + teste do mecanismo de timeout
#      (dados/piloto/), usado para justificar o timeout de 2000 ms;
#   3. matriz: 5 configurações x 5 repetições = 25 execuções (dados/*.csv),
#      intercaladas por repetição (rep 1 de todas, depois rep 2, ...);
#   4. teste funcional --teste-prioridade (dados/teste_prioridade/);
#   5. demonstração da política ingênua, fora da matriz (dados/ingenua/).
#
# Uso (a partir da raiz do projeto ou de qualquer lugar):
#   bash scripts/run_experimentos.sh
set -u

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$RAIZ/src"
DADOS="$RAIZ/dados"
BIN="$SRC/simulacao"
TIMEOUT_MS=2000
CFLAGS_CMD="gcc -std=c11 -O2 -Wall -Wextra -pthread *.c -o simulacao"

# Configurações: "elfos renas_ms"
CONFIGS=("6 10" "3 10" "12 10" "6 5" "6 30")
SEMENTES=(11 22 33 44 55)

mkdir -p "$DADOS"
# Os CSVs são abertos em modo de acréscimo: limpa a rodada anterior.
rm -f "$DADOS"/resumo.csv "$DADOS"/eventos.csv "$DADOS"/espera_elfos.csv
rm -rf "$DADOS/piloto" "$DADOS/teste_prioridade" "$DADOS/ingenua" "$DADOS/estresse"
mkdir -p "$DADOS/piloto" "$DADOS/teste_prioridade" "$DADOS/ingenua" "$DADOS/estresse"

# ---------- 1. ambiente e compilação ----------
{
    echo "data: $(date -Iseconds)"
    echo "maquina: $(hostname)"
    echo "cpu: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//')"
    echo "cpus_logicas (nproc): $(nproc)"
    echo "memoria: $(free -h | awk '/Mem:/ {print $2}')"
    echo "so: $(. /etc/os-release && echo "$PRETTY_NAME")"
    echo "kernel: $(uname -srm)"
    echo "gcc: $(gcc --version | head -n1)"
    echo "glibc: $(ldd --version | head -n1)"
    echo "python: $(python3 --version 2>&1)"
    echo "comando_compilacao: cd src && $CFLAGS_CMD"
    echo "timeout_ms: $TIMEOUT_MS"
} > "$DADOS/ambiente.txt"

echo ">> compilando: $CFLAGS_CMD"
( cd "$SRC" && gcc -std=c11 -O2 -Wall -Wextra -pthread *.c -o simulacao 2> "$DADOS/compilacao.txt" )
if [ $? -ne 0 ]; then
    cat "$DADOS/compilacao.txt"; echo "ERRO: compilação falhou"; exit 1
fi
if [ -s "$DADOS/compilacao.txt" ]; then
    echo "ATENÇÃO: a compilação gerou mensagens:"; cat "$DADOS/compilacao.txt"
else
    echo "compilacao: sem warnings" >> "$DADOS/ambiente.txt"
fi

# Roda uma execução sem abortar o script se ela falhar; registra o código.
rodar() {
    "$BIN" "$@"
    local rc=$?
    if [ $rc -ne 0 ]; then echo "   (código de saída $rc: $*)"; fi
    return 0
}

# ---------- 2. piloto ----------
echo ">> piloto (3 execuções por configuração, timeout $TIMEOUT_MS ms)"
for k in 1 2 3; do
    for cfg in "${CONFIGS[@]}"; do
        set -- $cfg
        rodar --elfos "$1" --renas-ms "$2" --rep "$k" --semente 0 \
              --timeout-ms "$TIMEOUT_MS" --out "$DADOS/piloto/" > /dev/null
    done
done
# Mecanismo de timeout: um limite de 5 ms tem de ser atingido e registrado.
echo ">> piloto: teste do mecanismo de timeout (--timeout-ms 5)"
mkdir -p "$DADOS/piloto/teste_timeout"
rodar --elfos 6 --renas-ms 10 --rep 1 --semente 0 --timeout-ms 5 \
      --out "$DADOS/piloto/teste_timeout/" | tee "$DADOS/piloto/teste_timeout/saida.txt"
awk -F, 'NR>1 { if ($8>m) m=$8; n++ } END { printf "piloto: %d execuções, maior T = %.3f ms\n", n, m }' \
    "$DADOS/piloto/resumo.csv" | tee "$DADOS/piloto/conclusao_piloto.txt"

# ---------- 3. matriz experimental ----------
echo ">> matriz: 5 configurações x 5 repetições"
for i in 0 1 2 3 4; do
    rep=$((i + 1)); sem=${SEMENTES[$i]}
    for cfg in "${CONFIGS[@]}"; do
        set -- $cfg
        rodar --elfos "$1" --renas-ms "$2" --rep "$rep" --semente "$sem" \
              --timeout-ms "$TIMEOUT_MS" --out "$DADOS/"
    done
done

# ---------- 4. teste funcional ----------
echo ">> teste funcional: --teste-prioridade (6 elfos, renas em 30 ms)"
CMD_TESTE="./simulacao --elfos 6 --renas-ms 30 --rep 1 --semente 11 --out ../dados/teste_prioridade/ --teste-prioridade"
( cd "$SRC" && { echo "\$ $CMD_TESTE"; $CMD_TESTE; echo "codigo_saida=$?"; } ) \
    | tee "$DADOS/teste_prioridade/saida.txt"

# ---------- 5. demonstração da política ingênua (fora da matriz) ----------
echo ">> demonstração: política ingênua (elfos primeiro), mesmo cenário do teste"
CMD_ING="./simulacao --elfos 6 --renas-ms 30 --rep 1 --semente 11 --out ../dados/ingenua/ --teste-prioridade --ingenua"
( cd "$SRC" && { echo "\$ $CMD_ING"; $CMD_ING; echo "codigo_saida=$?"; } ) \
    | tee "$DADOS/ingenua/saida.txt"

# ---------- 6. estresse de encerramento (fora da matriz) ----------
# 100 execuções de 3 configurações extremas: nenhuma pode travar ou violar.
echo ">> estresse: 100 x {3 elfos/10 ms, 12 elfos/5 ms, 12 elfos/30 ms}"
for k in $(seq 1 100); do
    for cfg in "3 10" "12 5" "12 30"; do
        set -- $cfg
        rodar --elfos "$1" --renas-ms "$2" --rep "$k" --semente 0 \
              --timeout-ms "$TIMEOUT_MS" --out "$DADOS/estresse/" > /dev/null
    done
done
awk -F, 'NR>1 { c[$20]++; n++; if ($8>m) m=$8 } END { for (s in c) printf "estresse: %s = %d de %d\n", s, c[s], n; printf "estresse: maior T = %.3f ms\n", m }' \
    "$DADOS/estresse/resumo.csv" | tee "$DADOS/estresse/conclusao_estresse.txt"

echo ">> concluído. Status da matriz:"
awk -F, 'NR>1 { c[$20]++; n++ } END { for (s in c) printf "   %s: %d de %d\n", s, c[s], n }' "$DADOS/resumo.csv"
