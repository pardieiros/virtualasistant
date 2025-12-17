# Jarvas Terminal API

## Descrição

Serviço FastAPI para executar comandos whitelisted no host Proxmox de forma segura. Este serviço é utilizado pelo assistente virtual "Jarvas" para consultar o estado de LXCs (Linux Containers), VMs (Virtual Machines), containers Docker, e informações do sistema.

A API implementa uma política de segurança rigorosa através de uma whitelist de comandos permitidos, garantindo que apenas operações seguras e pré-aprovadas podem ser executadas no host.

## Base URL

```
http://<HOST>:8900
```

A porta padrão é `8900`, mas pode ser configurada através da variável de ambiente `JARVAS_TERMINAL_PORT`.

## Autenticação

A API utiliza autenticação via **Bearer Token** no header `Authorization`.

### Header de Autenticação

```
Authorization: Bearer <JARVAS_TERMINAL_TOKEN>
```

O token de autenticação deve ser configurado através da variável de ambiente `JARVAS_TERMINAL_TOKEN` ou através de um ficheiro `.env` no diretório do serviço.

**⚠️ Importante:** O token padrão (`CHANGE_THIS_TOKEN_IN_PRODUCTION`) deve ser alterado em ambiente de produção.

## Endpoints

### GET /

Endpoint de health check básico que retorna informações sobre o serviço.

**Resposta:**

```json
{
  "service": "Jarvas Terminal API",
  "version": "1.0.0",
  "status": "running"
}
```

**Exemplo:**

```bash
curl http://<HOST>:8900/
```

---

### GET /health

Endpoint de health check simplificado.

**Resposta:**

```json
{
  "status": "healthy"
}
```

**Exemplo:**

```bash
curl http://<HOST>:8900/health
```

---

### POST /api/system/terminal/run/

Executa um comando validado contra a whitelist de comandos permitidos.

**Autenticação:** Requerida (Bearer Token)

**Request Body (JSON):**

```json
{
  "command": "pct exec 103 -- docker ps -a",
  "filter_contains": "soketi"
}
```

**Campos:**

- `command` (string, obrigatório): Comando de linha de comandos a executar
- `filter_contains` (string, opcional): Substring para filtrar linhas do output. Se especificado, apenas linhas que contenham esta substring serão retornadas em `stdout` e `stderr`

**Resposta (JSON):**

```json
{
  "allowed": true,
  "command": ["pct", "exec", "103", "--", "docker", "ps", "-a"],
  "returncode": 0,
  "stdout": "LINHAS DO COMANDO (eventualmente filtradas)...",
  "stderr": "",
  "timestamp": "2025-12-07T22:21:46.123456"
}
```

**Campos da Resposta:**

- `allowed` (boolean): Indica se o comando foi permitido pela whitelist
- `command` (array): Lista de argumentos do comando após parsing
- `returncode` (integer): Código de retorno do comando (0 = sucesso, -1 = erro/timeout)
- `stdout` (string): Output padrão do comando (pode estar filtrado se `filter_contains` foi especificado)
- `stderr` (string): Output de erro do comando (pode estar filtrado se `filter_contains` foi especificado)
- `timestamp` (string): Timestamp ISO 8601 da execução

**Códigos de Erro:**

- `400`: Comando vazio
- `401`: Token de autenticação ausente
- `403`: Token de autenticação inválido

**Exemplo com curl:**

```bash
curl -X POST http://<HOST>:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "pct exec 103 -- docker ps -a",
    "filter_contains": "soketi"
  }'
```

## Comandos Permitidos (Whitelist)

A API mantém uma whitelist rigorosa de comandos permitidos. Apenas os comandos e flags explicitamente listados podem ser executados.

### docker

**Subcomandos permitidos:**
- `ps`: Listar containers
- `logs`: Ver logs de um container
- `restart`: Reiniciar um container

**Flags permitidas:**
- `-a`, `--all`: Mostrar todos os containers (incluindo parados)
- `--tail <N>`: Mostrar últimas N linhas dos logs
- `-n <N>`: Mostrar últimas N linhas dos logs

**Regras especiais:**
- Para `docker logs` e `docker restart`, é necessário especificar o nome do container
- O nome do container deve corresponder ao padrão: `^[a-zA-Z0-9_-]+$` (alfanumérico, underscore, hífen)

**Exemplos:**
```bash
docker ps
docker ps -a
docker logs --tail 100 mycontainer
docker restart mycontainer
```

### pct (Proxmox Container Toolkit)

**Subcomandos permitidos:**
- `list`: Listar todos os LXCs
- `status <LXC_ID>`: Ver estado de um LXC
- `start <LXC_ID>`: Iniciar um LXC
- `stop <LXC_ID>`: Parar um LXC
- `exec <LXC_ID> -- docker ps [-a]`: Executar comando docker dentro de um LXC

**Regras especiais:**

1. **pct list**: Não requer argumentos adicionais

2. **pct status/start/stop**: Requer um ID numérico válido
   - Formato do ID: `^\d+$` (apenas dígitos)

3. **pct exec**: Estrutura rígida e validada
   - Formato: `pct exec <LXC_ID> -- docker ps [-a]`
   - Apenas `docker ps` e `docker ps -a` são permitidos dentro do `pct exec`
   - Não são permitidos pipes, outros comandos, ou flags adicionais
   - O separador `--` é obrigatório

**Exemplos:**
```bash
pct list
pct status 101
pct start 101
pct stop 101
pct exec 103 -- docker ps
pct exec 103 -- docker ps -a
```

### qm (QEMU/KVM Manager)

**Subcomandos permitidos:**
- `list`: Listar todas as VMs
- `status <VM_ID>`: Ver estado de uma VM
- `start <VM_ID>`: Iniciar uma VM
- `stop <VM_ID>`: Parar uma VM

**Regras especiais:**
- Para `status`, `start`, e `stop`, é necessário especificar um ID numérico válido
- Formato do ID: `^\d+$` (apenas dígitos)

**Exemplos:**
```bash
qm list
qm status 100
qm start 100
qm stop 100
```

### df (Disk Free)

**Flags permitidas:**
- `-h`, `--human-readable`: Mostrar tamanhos em formato legível

**Exemplos:**
```bash
df
df -h
df --human-readable
```

### free (Memory Usage)

**Flags permitidas:**
- `-m`, `--mega`: Mostrar em megabytes
- `-g`, `--giga`: Mostrar em gigabytes
- `-h`, `--human`: Mostrar em formato legível

**Exemplos:**
```bash
free
free -m
free -h
```

### uptime

**Sem flags ou argumentos adicionais permitidos.**

**Exemplo:**
```bash
uptime
```

## Filtragem de Output

A API suporta filtragem opcional do output através do campo `filter_contains` no request. Esta funcionalidade permite filtrar linhas do output que contenham uma substring específica.

**Características:**
- A filtragem é feita em Python, de forma segura, sem utilizar pipes ou shell
- Aplica-se tanto a `stdout` como a `stderr`
- A filtragem é case-sensitive (distingue maiúsculas/minúsculas)
- Apenas linhas que contenham a substring são retornadas

**Exemplo:**

Request:
```json
{
  "command": "pct exec 103 -- docker ps -a",
  "filter_contains": "soketi"
}
```

Se o output original contiver:
```
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    NAMES
abc123         nginx     ...       ...       ...       soketi-app
def456         redis     ...       ...       ...       redis-cache
```

O output filtrado será:
```
abc123         nginx     ...       ...       ...       soketi-app
```

## Exemplos Práticos

### 1. Listar todos os LXCs

```bash
curl -X POST http://<HOST>:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"command": "pct list"}'
```

**Resposta:**
```json
{
  "allowed": true,
  "command": ["pct", "list"],
  "returncode": 0,
  "stdout": "VMID       Status     Lock         Name\n  101       running                 lxc-nginx\n  102       stopped                 lxc-redis",
  "stderr": "",
  "timestamp": "2025-12-07T22:21:46.123456"
}
```

### 2. Ver estado de um LXC

```bash
curl -X POST http://<HOST>:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"command": "pct status 101"}'
```

### 3. Ver containers Docker dentro de um LXC

```bash
curl -X POST http://<HOST>:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"command": "pct exec 103 -- docker ps -a"}'
```

### 4. Filtrar output para mostrar apenas linhas com "soketi"

```bash
curl -X POST http://<HOST>:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "pct exec 103 -- docker ps -a",
    "filter_contains": "soketi"
  }'
```

### 5. Ver logs de um container Docker

```bash
curl -X POST http://<HOST>:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"command": "docker logs --tail 50 mycontainer"}'
```

### 6. Ver uso de disco

```bash
curl -X POST http://<HOST>:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"command": "df -h"}'
```

### 7. Ver uso de memória

```bash
curl -X POST http://<HOST>:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"command": "free -h"}'
```

## Segurança

### Políticas de Segurança Implementadas

1. **Whitelist de Comandos**: Apenas comandos explicitamente permitidos podem ser executados
2. **Validação Rigorosa**: Todos os argumentos são validados contra padrões seguros
3. **Sem Shell**: Os comandos são executados diretamente via `subprocess.run()` com `shell=False`, prevenindo injeção de comandos
4. **Timeout**: Todos os comandos têm um timeout configurável (padrão: 20 segundos)
5. **Autenticação**: Acesso protegido por Bearer Token
6. **Logging**: Todas as operações são registadas para auditoria

### Comandos Não Permitidos

- Comandos não listados na whitelist
- Pipes (`|`) ou redirecionamentos (`>`, `>>`, `<`)
- Operadores lógicos (`&&`, `||`, `;`)
- Comandos com argumentos não validados
- Execução de scripts ou binários arbitrários

### Mensagens de Erro

Quando um comando é rejeitado, a resposta inclui:
- `allowed: false`
- `returncode: -1`
- `stderr`: Mensagem de erro descritiva (em português ou inglês)

**Exemplo de comando rejeitado:**
```json
{
  "allowed": false,
  "command": [],
  "returncode": -1,
  "stdout": "",
  "stderr": "Comando não permitido pela política de segurança.",
  "timestamp": "2025-12-07T22:21:46.123456"
}
```

## Configuração

### Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `JARVAS_TERMINAL_PORT` | Porta do servidor | `8900` |
| `JARVAS_TERMINAL_TOKEN` | Token de autenticação | `CHANGE_THIS_TOKEN_IN_PRODUCTION` |
| `JARVAS_TERMINAL_TIMEOUT` | Timeout de comandos (segundos) | `20` |
| `LOG_LEVEL` | Nível de logging | `INFO` |
| `LOG_FILE` | Caminho do ficheiro de log | `/opt/jarvas-terminal/logs/jarvas_terminal.log` |

### Ficheiro .env

As variáveis podem ser definidas num ficheiro `.env` no diretório do serviço:

```env
JARVAS_TERMINAL_PORT=8900
JARVAS_TERMINAL_TOKEN=seu_token_seguro_aqui
JARVAS_TERMINAL_TIMEOUT=20
LOG_LEVEL=INFO
LOG_FILE=/opt/jarvas-terminal/logs/jarvas_terminal.log
```

## Limitações

1. **Timeout**: Comandos que excedam o timeout configurado serão terminados
2. **Output Size**: O output é limitado pela memória disponível (não há limite explícito)
3. **Comandos Interativos**: Comandos que requerem input interativo não são suportados
4. **Comandos de Longa Duração**: Comandos que demorem mais que o timeout serão terminados

## Suporte

Para questões ou problemas, consulte:
- Logs do serviço: `/opt/jarvas-terminal/logs/jarvas_terminal.log`
- Documentação de segurança: `SECURITY.md`
- Documentação de instalação: `INSTALL.md`




