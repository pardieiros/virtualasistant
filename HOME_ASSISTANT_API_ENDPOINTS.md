# Home Assistant API Endpoints

## 📋 Lista de Endpoints Disponíveis

### 1. **API Status** ✅
- **Endpoint:** `GET /api/`
- **Descrição:** Verifica se a API está a funcionar
- **Resposta:** `{"message": "API running."}`
- **Uso:** Verificar conectividade

### 2. **Configuration Info** ✅
- **Endpoint:** `GET /api/config`
- **Descrição:** Obtém informações sobre a configuração do Home Assistant
- **Retorna:**
  - Location name
  - Timezone
  - Version
  - Outras configurações do sistema
- **Uso:** Obter informações gerais do sistema

### 3. **All States** ✅
- **Endpoint:** `GET /api/states`
- **Descrição:** Obtém o estado atual de TODAS as entidades
- **Retorna:** Lista de todas as entidades com:
  - `entity_id` (ex: `light.living_room`)
  - `state` (ex: `on`, `off`, `25.5`)
  - `attributes` (temperatura, brilho, cor, etc.)
- **Uso:** 
  - Monitorizar todos os dispositivos
  - Verificar estados de sensores
  - Listar todas as entidades disponíveis

### 4. **Get Specific Entity State** ✅
- **Endpoint:** `GET /api/states/<entity_id>`
- **Descrição:** Obtém o estado de uma entidade específica
- **Exemplo:** `GET /api/states/light.living_room`
- **Retorna:** Estado completo da entidade com todos os atributos
- **Uso:**
  - Verificar estado de um dispositivo específico
  - Obter atributos detalhados (temperatura, brilho, cor, etc.)

### 5. **Update Entity State** 
- **Endpoint:** `POST /api/states/<entity_id>`
- **Descrição:** Atualiza o estado de uma entidade
- **Body:** 
  ```json
  {
    "state": "on",
    "attributes": {
      "brightness": 255,
      "color_name": "red"
    }
  }
  ```
- **Uso:** Alterar estado de dispositivos diretamente

### 6. **All Services** ✅
- **Endpoint:** `GET /api/services`
- **Descrição:** Lista todos os serviços disponíveis organizados por domínio
- **Retorna:** Objeto com domínios e seus serviços
- **Exemplo de domínios:**
  - `light`: turn_on, turn_off, toggle
  - `switch`: turn_on, turn_off, toggle
  - `climate`: set_temperature, set_hvac_mode
  - `homeassistant`: check_config, reload_config_entry
- **Uso:** Descobrir quais serviços estão disponíveis

### 7. **Call Service** ✅
- **Endpoint:** `POST /api/services/<domain>/<service>`
- **Descrição:** Chama um serviço específico
- **Exemplos:**
  - `POST /api/services/light/turn_on`
  - `POST /api/services/light/turn_off`
  - `POST /api/services/switch/toggle`
  - `POST /api/services/climate/set_temperature`
- **Body:** 
  ```json
  {
    "entity_id": "light.living_room",
    "brightness": 255,
    "color_name": "red"
  }
  ```
- **Uso:** 
  - Ligar/desligar luzes
  - Controlar interruptores
  - Ajustar temperatura
  - Executar qualquer ação disponível

### 8. **All Components** ✅
- **Endpoint:** `GET /api/components`
- **Descrição:** Lista todos os componentes/integrações carregados
- **Retorna:** Lista de nomes de componentes
- **Uso:** Ver quais integrações estão ativas

### 9. **All Events** ✅
- **Endpoint:** `GET /api/events`
- **Descrição:** Lista todos os tipos de eventos disponíveis
- **Retorna:** Lista de eventos e número de listeners
- **Uso:** Descobrir quais eventos podem ser disparados

### 10. **Fire Event**
- **Endpoint:** `POST /api/events/<event_type>`
- **Descrição:** Dispara um evento personalizado
- **Body:**
  ```json
  {
    "data": {
      "custom_parameter": "value"
    }
  }
  ```
- **Uso:** Disparar eventos para acionar automações

### 11. **History**
- **Endpoint:** `GET /api/history/period?filter_entity_id=<entity_id>&end_time=<timestamp>`
- **Descrição:** Obtém histórico de estados
- **Parâmetros:**
  - `filter_entity_id`: ID da entidade (obrigatório)
  - `end_time`: Timestamp de fim (opcional)
- **Uso:** Ver histórico de mudanças de estado

### 12. **Conversation Process**
- **Endpoint:** `POST /api/conversation/process`
- **Descrição:** Processa uma frase e retorna resposta
- **Body:**
  ```json
  {
    "text": "turn on the living room light",
    "language": "en"
  }
  ```
- **Uso:** Usar assistente de voz/texto do Home Assistant

## 🎯 Casos de Uso Comuns

### Controlar Luzes
```bash
POST /api/services/light/turn_on
Body: {
  "entity_id": "light.living_room",
  "brightness": 255,
  "color_name": "warm"
}
```

### Controlar Interruptores
```bash
POST /api/services/switch/turn_on
Body: {
  "entity_id": "switch.kitchen"
}
```

### Ajustar Temperatura
```bash
POST /api/services/climate/set_temperature
Body: {
  "entity_id": "climate.living_room",
  "temperature": 22
}
```

### Verificar Estado
```bash
GET /api/states/light.living_room
```

### Listar Todas as Entidades
```bash
GET /api/states
```

## 📊 Resultados do Teste

- ✅ **7/8 endpoints testados com sucesso**
- ✅ **69 entidades** encontradas
- ✅ **40 domínios** com serviços disponíveis
- ✅ **114 componentes** carregados
- ✅ **16 tipos de eventos** disponíveis

## 🔐 Autenticação

Todos os endpoints (exceto `/api/`) requerem autenticação:

```
Authorization: Bearer <long_lived_token>
Content-Type: application/json
```

## 📝 Notas

- O endpoint `/api/history/period` requer parâmetros específicos
- Alguns serviços podem falhar se os parâmetros estiverem incorretos
- Use `GET /api/services` para descobrir serviços disponíveis
- Use `GET /api/states` para descobrir entity_ids disponíveis



