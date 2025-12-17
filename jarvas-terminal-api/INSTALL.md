# Instalação Rápida - Jarvas Terminal API

## Comandos de Instalação no Proxmox Host

Execute os seguintes comandos no host Proxmox:

### 1. Criar Diretório e Estrutura

```bash
sudo mkdir -p /opt/jarvas-terminal/logs
cd /opt/jarvas-terminal
```

### 2. Copiar Ficheiros

Copie os seguintes ficheiros para `/opt/jarvas-terminal/`:
- `jarvas_terminal_api.py`
- `requirements.txt`
- `env.example`

### 3. Criar Virtual Environment e Instalar Dependências

```bash
cd /opt/jarvas-terminal
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar Ambiente

```bash
# Copiar ficheiro de exemplo
cp env.example .env

# Gerar token forte (recomendado)
TOKEN=$(openssl rand -hex 32)
echo "Token gerado: $TOKEN"

# Editar .env e colocar o token
nano .env
```

No ficheiro `.env`, defina:
- `JARVAS_TERMINAL_TOKEN` - Cole o token gerado acima
- `JARVAS_TERMINAL_PORT` - Porta (padrão: 8900)
- Outras configurações conforme necessário

### 5. Definir Permissões

```bash
# Tornar script executável
chmod +x /opt/jarvas-terminal/jarvas_terminal_api.py

# Proteger ficheiro .env
chmod 600 /opt/virtualasistant/jarvas-terminal-api/.env

# Definir propriedade (ajustar user/group se necessário)
sudo chown -R root:root opt/virtualasistant/jarvas-terminal-api
```

### 6. Instalar e Ativar Serviço Systemd

```bash
# Copiar ficheiro de serviço
sudo cp jarvas-terminal.service /etc/systemd/system/

# Recarregar systemd
sudo systemctl daemon-reload

# Ativar serviço para iniciar no boot
sudo systemctl enable jarvas-terminal.service

# Iniciar o serviço
sudo systemctl start jarvas-terminal.service

# Verificar status
sudo systemctl status jarvas-terminal.service
```

### 7. Verificar Instalação

```bash
# Ver logs em tempo real
sudo journalctl -u jarvas-terminal.service -f

# Ou verificar ficheiro de log
tail -f /opt/jarvas-terminal/logs/jarvas_terminal.log

# Testar endpoint de health
curl http://localhost:8900/health
```

## Testar API

### Exemplo: Ver Containers Docker

```bash
# Substituir YOUR_TOKEN_HERE pelo token do .env
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "docker ps"}'
```

### Exemplo: Ver Logs do SearXNG

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "docker logs --tail 50 searxng"}'
```

### Exemplo: Listar LXCs

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "pct list"}'
```

## Gestão do Serviço

```bash
# Reiniciar serviço
sudo systemctl restart jarvas-terminal.service

# Parar serviço
sudo systemctl stop jarvas-terminal.service

# Ver status
sudo systemctl status jarvas-terminal.service

# Ver logs
sudo journalctl -u jarvas-terminal.service -n 100
```

## Resolução de Problemas

### Serviço não inicia

1. Verificar logs:
   ```bash
   sudo journalctl -u jarvas-terminal.service -n 50
   ```

2. Verificar Python e dependências:
   ```bash
   /opt/jarvas-terminal/venv/bin/python3 --version
   /opt/jarvas-terminal/venv/bin/pip list
   ```

3. Testar manualmente:
   ```bash
   cd /opt/jarvas-terminal
   source venv/bin/activate
   python3 jarvas_terminal_api.py
   ```

### Erro de autenticação

- Verificar se o token no `.env` corresponde ao usado no request
- Verificar formato do header: `Authorization: Bearer <TOKEN>`

### Comando não permitido

- Verificar se o comando está na whitelist
- Verificar sintaxe exata do comando
- Consultar logs para mensagens de validação









