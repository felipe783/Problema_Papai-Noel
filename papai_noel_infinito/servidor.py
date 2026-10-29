#!/usr/bin/env python3
"""Servidor da interface do Papai Noel infinito (somente biblioteca padrão).

Lança o binário C como subprocesso, lê os eventos JSON Lines do stdout e os
retransmite para o navegador via Server-Sent Events (/api/eventos). Os
comandos da interface (pausar, retomar, velocidade) são escritos no stdin
do processo; iniciar/parar trocam o processo.

    python3 servidor.py [--porta 8000]
"""

import argparse
import collections
import json
import os
import queue
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SRC = RAIZ / "src"
BIN = SRC / "noel_infinito"
WEB = RAIZ / "web"

# nome do campo na interface -> (flag, mínimo, máximo)
PARAMS = {
    "elfos": ("--elfos", 3, 60),
    "ajuda": ("--ajuda", 0, 600000),
    "preparo": ("--preparo", 0, 600000),
    "viagem": ("--viagem", 0, 600000),
    "semente": ("--semente", 0, 2000000000),
}
PARES = {"ferias": "--ferias", "trabalho": "--trabalho"}


def compilar():
    """Compila o binário se ele não existir ou estiver mais velho que o código."""
    fontes = list(SRC.glob("*.c")) + list(SRC.glob("*.h"))
    if BIN.exists() and BIN.stat().st_mtime >= max(f.stat().st_mtime for f in fontes):
        return
    cmd = ["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-pthread",
           *map(str, sorted(SRC.glob("*.c"))), "-o", str(BIN)]
    print("compilando:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def montar_args(p):
    args = [str(BIN)]
    for nome, (flag, lo, hi) in PARAMS.items():
        if nome in p:
            args += [flag, str(max(lo, min(hi, int(p[nome]))))]
    for nome, flag in PARES.items():
        if nome in p:
            a, b = sorted(max(0, min(600000, int(v))) for v in p[nome])
            args += [flag, str(a), str(b)]
    if "velocidade" in p:
        args += ["--velocidade", str(max(0.1, min(50.0, float(p["velocidade"]))))]
    return args


class Simulacao:
    """Um processo de simulação por vez, com vários ouvintes SSE."""

    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.ouvintes = set()
        self.historico = collections.deque(maxlen=200)

    def _publicar(self, linha):
        with self.lock:
            self.historico.append(linha)
            for q in list(self.ouvintes):
                q.put(linha)

    def _ler(self, proc):
        for linha in proc.stdout:
            if proc is not self.proc:
                break
            self._publicar(linha.strip())
        proc.wait()
        if proc is self.proc:
            self._publicar(json.dumps({"ev": "processo_terminou", "quem": "ctl",
                                       "codigo": proc.returncode}))

    def iniciar(self, params):
        self.parar()
        args = montar_args(params)
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, bufsize=1)
        with self.lock:
            self.proc = proc
            self.historico.clear()
        for q in list(self.ouvintes):
            q.put(json.dumps({"ev": "reinicio", "quem": "ctl"}))
        threading.Thread(target=self._ler, args=(proc,), daemon=True).start()
        return args

    def comando(self, texto):
        proc = self.proc
        if not proc or proc.poll() is not None:
            return False
        try:
            proc.stdin.write(texto + "\n")
            proc.stdin.flush()
            return True
        except (BrokenPipeError, ValueError):
            return False

    def parar(self):
        proc = self.proc
        if not proc:
            return
        self.comando("sair")
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def rodando(self):
        return self.proc is not None and self.proc.poll() is None

    def ouvir(self):
        q = queue.Queue()
        with self.lock:
            for linha in self.historico:
                q.put(linha)
            self.ouvintes.add(q)
        return q

    def esquecer(self, q):
        with self.lock:
            self.ouvintes.discard(q)


SIM = Simulacao()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def log_message(self, fmt, *args):  # silencioso: o SSE geraria ruído
        pass

    def _json(self, codigo, obj):
        corpo = json.dumps(obj).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/api/estado":
            return self._json(200, {"rodando": SIM.rodando()})
        if self.path != "/api/eventos":
            return super().do_GET()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        q = SIM.ouvir()
        try:
            self.wfile.write(b": conectado\n\n")
            self.wfile.flush()
            while True:
                try:
                    linha = q.get(timeout=15)
                    self.wfile.write(f"data: {linha}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")  # mantém a conexão viva
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            SIM.esquecer(q)

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        try:
            corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"erro": "JSON inválido"})

        if self.path == "/api/iniciar":
            try:
                args = SIM.iniciar(corpo)
            except (TypeError, ValueError) as e:
                return self._json(400, {"erro": str(e)})
            return self._json(200, {"ok": True, "args": args[1:]})
        if self.path == "/api/parar":
            SIM.parar()
            return self._json(200, {"ok": True})
        if self.path in ("/api/pausar", "/api/retomar"):
            return self._json(200, {"ok": SIM.comando(self.path.rsplit("/", 1)[1])})
        if self.path == "/api/velocidade":
            try:
                v = max(0.1, min(50.0, float(corpo.get("v", 1))))
            except (TypeError, ValueError):
                return self._json(400, {"erro": "velocidade inválida"})
            return self._json(200, {"ok": SIM.comando(f"velocidade {v}")})
        self._json(404, {"erro": "rota desconhecida"})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--porta", type=int, default=int(os.environ.get("PORTA", 8000)))
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()

    compilar()
    srv = ThreadingHTTPServer((a.host, a.porta), Handler)
    srv.daemon_threads = True
    print(f"Papai Noel infinito em http://{a.host}:{a.porta}  (Ctrl+C para sair)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        SIM.parar()
        srv.server_close()


if __name__ == "__main__":
    main()
