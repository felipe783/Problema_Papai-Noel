/*
 * main.c — Problema do Papai Noel INFINITO (C11 + pthreads).
 *
 * Cria Noel, 9 renas e N elfos, que repetem seus ciclos para sempre.
 * Duas threads auxiliares controlam a execução:
 *   - controle: lê comandos em stdin (pausar, retomar, velocidade X, sair);
 *     EOF em stdin também encerra (o servidor que nos lançou morreu);
 *   - sinais: SIGINT/SIGTERM via sigwait, para encerrar limpo com resumo.
 * Os eventos saem em stdout como JSON Lines (ou texto, com --texto).
 */
#include "comum.h"

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "atores.h"
#include "relogio.h"
#include "saida.h"

static void uso(const char *prog)
{
    fprintf(stderr,
            "uso: %s [opções]\n"
            "  --elfos N              quantidade de elfos (%d..%d)            [10]\n"
            "  --ferias MIN MAX       férias de cada rena, ms                 [5000 10000]\n"
            "  --trabalho MIN MAX     trabalho do elfo até pedir ajuda, ms    [3000 12000]\n"
            "  --ajuda MS             duração de uma ajuda                    [1200]\n"
            "  --preparo MS           atrelar as renas ao trenó               [1000]\n"
            "  --viagem MS            duração da viagem                       [3000]\n"
            "  --semente S            semente dos sorteios                    [42]\n"
            "  --velocidade V         ms virtuais por ms real (0.1..50)       [1]\n"
            "  --duracao-s S          encerra após S s virtuais (0 = infinito) [0]\n"
            "  --texto                saída legível em vez de JSON\n"
            "comandos em stdin: pausar | retomar | velocidade V | sair\n",
            prog, MIN_ELFOS, MAX_ELFOS);
}

static int ler_int(const char *s, int min, int max, int *out)
{
    char *fim;
    long v = strtol(s, &fim, 10);
    if (*s == '\0' || *fim != '\0' || v < min || v > max)
        return 0;
    *out = (int)v;
    return 1;
}

static int ler_double(const char *s, double min, double max, double *out)
{
    char *fim;
    double v = strtod(s, &fim);
    if (*s == '\0' || *fim != '\0' || v < min || v > max)
        return 0;
    *out = v;
    return 1;
}

static int ler_args(int argc, char **argv, Config *c)
{
    *c = (Config){ .elfos = 10, .ferias_min = 5000, .ferias_max = 10000,
                   .trabalho_min = 3000, .trabalho_max = 12000,
                   .ajuda_ms = 1200, .preparo_ms = 1000, .viagem_ms = 3000,
                   .semente = 42, .velocidade = 1.0 };
    const int MS = 600000;
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        int resta = argc - i - 1, ok = 1, s = 0;
        if (!strcmp(a, "--elfos") && resta >= 1)
            ok = ler_int(argv[++i], MIN_ELFOS, MAX_ELFOS, &c->elfos);
        else if (!strcmp(a, "--ferias") && resta >= 2)
            ok = ler_int(argv[i + 1], 0, MS, &c->ferias_min) && ler_int(argv[i + 2], c->ferias_min, MS, &c->ferias_max), i += 2;
        else if (!strcmp(a, "--trabalho") && resta >= 2)
            ok = ler_int(argv[i + 1], 0, MS, &c->trabalho_min) && ler_int(argv[i + 2], c->trabalho_min, MS, &c->trabalho_max), i += 2;
        else if (!strcmp(a, "--ajuda") && resta >= 1)
            ok = ler_int(argv[++i], 0, MS, &c->ajuda_ms);
        else if (!strcmp(a, "--preparo") && resta >= 1)
            ok = ler_int(argv[++i], 0, MS, &c->preparo_ms);
        else if (!strcmp(a, "--viagem") && resta >= 1)
            ok = ler_int(argv[++i], 0, MS, &c->viagem_ms);
        else if (!strcmp(a, "--semente") && resta >= 1)
            ok = ler_int(argv[++i], 0, 2000000000, &s), c->semente = (unsigned)s;
        else if (!strcmp(a, "--velocidade") && resta >= 1)
            ok = ler_double(argv[++i], 0.1, 50, &c->velocidade);
        else if (!strcmp(a, "--duracao-s") && resta >= 1)
            ok = ler_double(argv[++i], 0, 1e7, &c->duracao_s);
        else if (!strcmp(a, "--texto"))
            c->texto = 1;
        else
            ok = 0;
        if (!ok) {
            fprintf(stderr, "argumento inválido ou incompleto: %s\n", a);
            return 0;
        }
    }
    return 1;
}

/* Encerramento: acorda quem dorme no relógio e quem espera nas cond vars. */
static void encerrar_tudo(Oficina *o)
{
    relogio_encerrar(o->rel);
    pthread_mutex_lock(&o->mutex);
    o->encerrar = 1;
    pthread_cond_broadcast(&o->cv_noel);
    pthread_cond_broadcast(&o->cv_renas);
    pthread_cond_broadcast(&o->cv_elfos);
    pthread_mutex_unlock(&o->mutex);
}

static void *thread_controle(void *arg)
{
    Oficina *o = arg;
    char linha[128];
    while (fgets(linha, sizeof linha, stdin)) {
        double v;
        linha[strcspn(linha, "\r\n")] = '\0';
        if (!strcmp(linha, "pausar") || !strcmp(linha, "p")) {
            relogio_pausar(o->rel, 1);
            pthread_mutex_lock(&o->mutex);
            emitir(o, "ctl", 0, "pausado", 0, "Simulação pausada");
            pthread_mutex_unlock(&o->mutex);
        } else if (!strcmp(linha, "retomar") || !strcmp(linha, "r")) {
            relogio_pausar(o->rel, 0);
            pthread_mutex_lock(&o->mutex);
            emitir(o, "ctl", 0, "retomado", 0, "Simulação retomada");
            pthread_mutex_unlock(&o->mutex);
        } else if ((!strncmp(linha, "velocidade ", 11) && ler_double(linha + 11, 0.1, 50, &v)) ||
                   (!strncmp(linha, "v ", 2) && ler_double(linha + 2, 0.1, 50, &v))) {
            relogio_velocidade(o->rel, v);
            pthread_mutex_lock(&o->mutex);
            emitir(o, "ctl", 0, "velocidade", 0, "Velocidade ajustada para %gx", v);
            pthread_mutex_unlock(&o->mutex);
        } else if (!strcmp(linha, "sair") || !strcmp(linha, "q")) {
            encerrar_tudo(o);
            return NULL;
        } else if (linha[0]) {
            fprintf(stderr, "comando desconhecido: %s\n", linha);
        }
    }
    /* EOF: sem --duracao-s, quem nos lançou morreu e devemos encerrar; com
     * duração (ex.: stdin = /dev/null), deixamos o tempo terminar. */
    if (o->cfg->duracao_s <= 0)
        encerrar_tudo(o);
    return NULL;
}

static void *thread_sinais(void *arg)
{
    sigset_t *conj = ((void **)arg)[1];
    int sig;
    sigwait(conj, &sig);
    encerrar_tudo(((void **)arg)[0]);
    return NULL;
}

int main(int argc, char **argv)
{
    Config cfg;
    if (!ler_args(argc, argv, &cfg)) {
        uso(argv[0]);
        return 64;
    }

    /* Bloqueia SIGINT/SIGTERM antes de criar threads: todas herdam a máscara
     * e só a thread de sinais os recebe, via sigwait. */
    sigset_t conj;
    sigemptyset(&conj);
    sigaddset(&conj, SIGINT);
    sigaddset(&conj, SIGTERM);
    pthread_sigmask(SIG_BLOCK, &conj, NULL);

    Relogio rel;
    relogio_iniciar(&rel, cfg.velocidade);

    static Oficina o; /* zerada: estático */
    o.cfg = &cfg;
    o.rel = &rel;
    pthread_mutex_init(&o.mutex, NULL);
    pthread_cond_init(&o.cv_noel, NULL);
    pthread_cond_init(&o.cv_elfos, NULL);
    pthread_cond_init(&o.cv_renas, NULL);
    o.rena = calloc(NUM_RENAS, sizeof *o.rena);
    o.elfo = calloc((size_t)cfg.elfos, sizeof *o.elfo);
    o.grupo_do_elfo = calloc((size_t)cfg.elfos, sizeof *o.grupo_do_elfo);
    o.t_pedido = calloc((size_t)cfg.elfos, sizeof *o.t_pedido);
    if (!o.rena || !o.elfo || !o.grupo_do_elfo || !o.t_pedido) {
        fprintf(stderr, "sem memória\n");
        return 1;
    }
    o.grupo_aberto = o.proximo_grupo = 1;
    GRUPO(&o, 1)->id = 1;

    pthread_mutex_lock(&o.mutex);
    emitir(&o, "ctl", 0, "inicio", 0, "Início: Noel dorme, %d elfos trabalham e as 9 renas estão de férias",
           cfg.elfos);
    pthread_mutex_unlock(&o.mutex);

    int total = 1 + NUM_RENAS + cfg.elfos;
    pthread_t *th = calloc((size_t)total, sizeof *th);
    ArgAtor *args = calloc((size_t)total, sizeof *args);
    if (!th || !args) {
        fprintf(stderr, "sem memória\n");
        return 1;
    }
    for (int i = 0; i < total; i++) {
        args[i].o = &o;
        args[i].id = i == 0 ? 0 : (i <= NUM_RENAS ? i - 1 : i - 1 - NUM_RENAS);
        args[i].semente = cfg.semente * 2654435761u + (unsigned)i;
        void *(*f)(void *) = i == 0 ? thread_noel : (i <= NUM_RENAS ? thread_rena : thread_elfo);
        if (pthread_create(&th[i], NULL, f, &args[i]) != 0) {
            fprintf(stderr, "falha ao criar a thread %d\n", i);
            encerrar_tudo(&o);
            total = i;
            break;
        }
    }

    pthread_t ctl, sig;
    void *arg_sinais[2] = { &o, &conj };
    pthread_create(&ctl, NULL, thread_controle, &o);
    pthread_create(&sig, NULL, thread_sinais, arg_sinais);
    pthread_detach(ctl); /* bloqueadas em fgets/sigwait: não dá para juntá-las */
    pthread_detach(sig);

    /* Duração em tempo virtual (pausas não contam). Sem duração, espera o
     * encerramento vindo de stdin ou de um sinal. */
    relogio_dormir(&rel, cfg.duracao_s > 0 ? cfg.duracao_s * 1000.0 : 1e15);
    encerrar_tudo(&o);

    for (int i = 0; i < total; i++)
        pthread_join(th[i], NULL);

    imprimir_resumo(&o);
    int status = o.violacoes ? 2 : 0;
    free(th);
    free(args);
    return status;
}
