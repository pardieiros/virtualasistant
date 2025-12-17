# Segurança - Jarvas Terminal API

## ⚠️ Avisos Importantes

Este serviço permite execução de comandos no sistema host Proxmox. **SEMPRE** siga estas práticas de segurança:

## 1. Whitelist de Comandos

### Porquê é Crítico

A whitelist é a **primeira linha de defesa** contra execução de comandos maliciosos. Apenas comandos explicitamente permitidos podem ser executados.

### Como Funciona

- Todos os comandos são validados contra `COMMAND_WHITELIST` antes da execução
- Apenas binários, subcomandos e flags permitidos são aceites
- Argumentos são validados (IDs numéricos, nomes de containers, etc.)
- Comandos rejeitados retornam erro sem execução

### Riscos de Modificar a Whitelist

**NUNCA** adicione comandos perigosos à whitelist, tais como:
- `rm -rf` ou qualquer comando de remoção
- `shutdown`, `reboot`, `poweroff`
- `dd` ou outros comandos de baixo nível
- Qualquer comando que permita escrita de ficheiros arbitrários
- Comandos que permitam escalada de privilégios

## 2. Autenticação por Token

### Boas Práticas

1. **Gere um token forte**:
   ```bash
   openssl rand -hex 32
   ```

2. **Nunca commite o token**:
   - Use `.env` file (já está no `.gitignore`)
   - Ou variável de ambiente do sistema
   - Nunca coloque o token no código

3. **Rotacione o token periodicamente**:
   - Mude o token a cada 3-6 meses
   - Ou imediatamente se suspeitar de compromisso

4. **Use HTTPS**:
   - Se expor fora da LAN, use nginx com SSL/TLS
   - Nunca envie tokens em texto plano pela internet

## 3. Isolamento de Rede

### Recomendações

1. **Apenas na LAN**:
   - Configure firewall para bloquear acesso externo
   - Use apenas IPs locais (192.168.x.x, 10.x.x.x)

2. **Via VPN (Recomendado)**:
   - Use WireGuard ou outra VPN
   - Apenas clientes autenticados na VPN podem aceder

3. **Nunca exponha à Internet**:
   - Não abra portas no router
   - Não use port forwarding sem VPN

### Exemplo de Firewall (iptables)

```bash
# Permitir apenas LAN local
sudo iptables -A INPUT -p tcp --dport 8900 -s 192.168.1.0/24 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8900 -j DROP
```

## 4. Prevenção de Shell Injection

### Medidas Implementadas

1. **`shell=False`**: Comandos nunca são executados através de shell
2. **`shlex.split()`**: Parsing seguro de argumentos
3. **Validação estrita**: Apenas argumentos validados são executados

### O que NÃO fazer

❌ **NUNCA** use `shell=True`:
```python
# PERIGOSO - NUNCA FAZER ISTO
subprocess.run(command, shell=True)
```

❌ **NUNCA** concatene comandos:
```python
# PERIGOSO
os.system(f"docker {user_input}")
```

✅ **SEMPRE** use parsing seguro:
```python
# SEGURO
parsed = shlex.split(command)
subprocess.run(parsed, shell=False)
```

## 5. Timeout de Comandos

### Configuração

- Timeout padrão: 20 segundos
- Configurável via `JARVAS_TERMINAL_TIMEOUT` no `.env`

### Porquê é Importante

- Previne comandos que ficam "pendurados"
- Protege contra DoS (Denial of Service)
- Garante resposta rápida da API

## 6. Logging e Auditoria

### O que é Registado

- Todos os comandos pedidos (comando, allowed/not allowed)
- Erros e timeouts
- Tentativas de autenticação falhadas
- Timestamps de todas as operações

### Revisão de Logs

Revise regularmente os logs para:
- Comandos suspeitos ou não autorizados
- Múltiplas tentativas de autenticação falhadas
- Padrões anómalos de uso

```bash
# Ver comandos executados
sudo journalctl -u jarvas-terminal.service | grep "Command"

# Ver tentativas falhadas
sudo journalctl -u jarvas-terminal.service | grep "Invalid token"
```

## 7. Permissões do Sistema

### Recomendações

1. **User do serviço**:
   - Atualmente: `root` (necessário para `pct` e `qm`)
   - Considere criar user dedicado com sudoers se possível

2. **Permissões de ficheiros**:
   ```bash
   chmod 600 /opt/jarvas-terminal/.env
   chmod 755 /opt/jarvas-terminal/jarvas_terminal_api.py
   ```

3. **Diretório de logs**:
   ```bash
   chmod 755 /opt/jarvas-terminal/logs
   ```

## 8. Integração com Jarvas

### Boas Práticas na Integração

1. **Armazene o token de forma segura**:
   - Use variáveis de ambiente
   - Ou ficheiro de configuração com permissões restritas

2. **Valide respostas**:
   - Verifique `allowed` antes de usar resultados
   - Trate erros adequadamente

3. **Rate limiting**:
   - Implemente rate limiting no lado do Jarvas
   - Não faça demasiados pedidos em sequência

4. **Error handling**:
   - Trate timeouts
   - Trate erros de rede
   - Não exponha tokens em logs

## 9. Checklist de Segurança

Antes de colocar em produção:

- [ ] Token forte gerado e configurado
- [ ] `.env` com permissões 600
- [ ] Firewall configurado (apenas LAN/VPN)
- [ ] Whitelist revisada (sem comandos perigosos)
- [ ] Logs configurados e acessíveis
- [ ] Serviço testado com comandos válidos
- [ ] Serviço testado com comandos inválidos (deve rejeitar)
- [ ] Timeout configurado adequadamente
- [ ] Backup do token em local seguro
- [ ] Documentação de procedimentos de emergência

## 10. Procedimentos de Emergência

### Se o token for comprometido:

1. **Imediatamente**:
   ```bash
   sudo systemctl stop jarvas-terminal.service
   ```

2. **Gerar novo token**:
   ```bash
   openssl rand -hex 32
   ```

3. **Atualizar `.env`**:
   ```bash
   nano /opt/jarvas-terminal/.env
   # Atualizar JARVAS_TERMINAL_TOKEN
   ```

4. **Reiniciar serviço**:
   ```bash
   sudo systemctl start jarvas-terminal.service
   ```

5. **Atualizar token no Jarvas** (se aplicável)

### Se detetar atividade suspeita:

1. Parar o serviço imediatamente
2. Revisar logs:
   ```bash
   sudo journalctl -u jarvas-terminal.service --since "1 hour ago"
   ```
3. Verificar sistema por compromisso
4. Alterar token
5. Revisar whitelist
6. Reiniciar serviço apenas após investigação

## Conclusão

Este serviço é **poderoso mas perigoso** se mal configurado. Siga sempre estas práticas:

1. ✅ Whitelist restritiva
2. ✅ Token forte e secreto
3. ✅ Apenas LAN/VPN
4. ✅ Logging ativo
5. ✅ Revisão regular

**Quando em dúvida, seja mais restritivo!**









