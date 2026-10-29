CC      ?= gcc
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra -pthread
SRC     := $(wildcard src/*.c)
HDR     := $(wildcard src/*.h)
BIN     := src/noel_infinito

.PHONY: all run web clean

all: $(BIN)

$(BIN): $(SRC) $(HDR)
	$(CC) $(CFLAGS) $(SRC) -o $@

# Terminal: saída legível (Ctrl+C encerra com resumo)
run: $(BIN)
	./$(BIN) --texto --velocidade 4

# Interface web em http://localhost:8000
web: $(BIN)
	python3 servidor.py

clean:
	rm -f $(BIN)
