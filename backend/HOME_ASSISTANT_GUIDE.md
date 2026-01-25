# Home Assistant - Guia de Utilização para User 1

Este documento descreve todas as funcionalidades disponíveis para o utilizador 1 através da interface Home Assistant e dos endpoints da API.

## 📋 Índice

1. [Os Teus Dispositivos](#os-teus-dispositivos)
2. [Configuração Inicial](#configuração-inicial)
3. [Visualizar Dispositivos](#visualizar-dispositivos)
4. [Controlar Dispositivos](#controlar-dispositivos)
5. [Gerir Aliases](#gerir-aliases)
6. [Exemplos Práticos por Tipo de Dispositivo](#exemplos-práticos-por-tipo-de-dispositivo)
7. [Endpoints da API](#endpoints-da-api)

---

## 🏠 Os Teus Dispositivos

Lista completa dos dispositivos configurados no teu Home Assistant:

### Ar Condicionados (Climate) - 3 dispositivos
- `climate.sala` - Sala (Estado: heat)
- `climate.quarto` - Quarto (Estado: heat)
- `climate.cozinha` - Cozinha (Estado: off)

### Interruptores (Switch) - 6 dispositivos
- `switch.sala_ligar_desligar` - Sala Ligar/Desligar (Estado: on)
- `switch.sala_poupanca_de_energia` - Sala Poupança de energia (Estado: off)
- `switch.quarto_ligar_desligar` - Quarto Ligar/Desligar (Estado: on)
- `switch.quarto_poupanca_de_energia` - Quarto Poupança de energia (Estado: off)
- `switch.cozinha_ligar_desligar` - Cozinha Ligar/Desligar (Estado: off)
- `switch.cozinha_poupanca_de_energia` - Cozinha Poupança de energia (Estado: off)

### Media Players - 3 dispositivos
- `media_player.meobox_4k_diw377` - MEOBox 4K (DIW377) (Estado: unavailable)
- `media_player.pen_de_transmissao_mi_tv` - Pen de transmissão Mi TV (Estado: off)
- `media_player.pen_de_transmissao_mi_tv_2` - Pen de transmissão Mi TV (Estado: on)
- `media_player.hisense_vidaa_tv` - Hisense VIDAA TV (Estado: unavailable)

### Remote Control - 1 dispositivo
- `remote.pen_de_transmissao_mi_tv` - Pen de transmissão Mi TV (Estado: on)

### Numbers (Valores Configuráveis) - 9 dispositivos
**Sala:**
- `number.sala_programar_a_ligar` - Programar a ligar
- `number.sala_programar_desligar` - Programar desligar
- `number.sala_temporizador_de_sono` - Temporizador de sono

**Quarto:**
- `number.quarto_programar_a_ligar` - Programar a ligar
- `number.quarto_programar_desligar` - Programar desligar
- `number.quarto_temporizador_de_sono` - Temporizador de sono

**Cozinha:**
- `number.cozinha_programar_a_ligar` - Programar a ligar
- `number.cozinha_programar_desligar` - Programar desligar
- `number.cozinha_temporizador_de_sono` - Temporizador de sono

### Sensores (Apenas Leitura) - Múltiplos dispositivos
**Sun:**
- `sensor.sun_next_dawn` - Próximo amanhecer
- `sensor.sun_next_dusk` - Próximo pôr do sol
- `sensor.sun_next_midnight` - Próxima meia-noite
- `sensor.sun_next_noon` - Próximo meio-dia
- `sensor.sun_next_rising` - Próximo nascer do sol
- `sensor.sun_next_setting` - Próximo pôr do sol

**Backup:**
- `sensor.backup_backup_manager_state` - Estado do gestor de backup (Estado: idle)
- `sensor.backup_next_scheduled_automatic_backup` - Próximo backup automático agendado
- `sensor.backup_last_successful_automatic_backup` - Último backup automático bem-sucedido
- `sensor.backup_last_attempted_automatic_backup` - Última tentativa de backup automático

**Programação:**
- `sensor.sala_programar_a_ligar` - Sala Programar a ligar
- `sensor.sala_programar_desligar` - Sala Programar desligar
- `sensor.sala_temporizador_de_sono` - Sala Temporizador de sono
- `sensor.quarto_programar_a_ligar` - Quarto Programar a ligar
- `sensor.quarto_programar_desligar` - Quarto Programar desligar
- `sensor.quarto_temporizador_de_sono` - Quarto Temporizador de sono
- `sensor.cozinha_programar_a_ligar` - Cozinha Programar a ligar
- `sensor.cozinha_programar_desligar` - Cozinha Programar desligar
- `sensor.cozinha_temporizador_de_sono` - Cozinha Temporizador de sono

**Outros:**
- `weather.forecast_inicio` - Previsão do tempo (Estado: rainy)

### Outros Dispositivos
- `todo.lista_de_compras` - Lista de Compras (Estado: 0)
- `person.casa_ines` - Casa Ines (Estado: unknown)
- `zone.home` - Início (Estado: 0)
- `sun.sun` - Sun (Estado: below_horizon)
- `conversation.home_assistant` - Home Assistant (Estado: unknown)
- `event.backup_automatic_backup` - Backup Automatic backup
- `event.sala_notificacao` - Sala Notificação
- `event.quarto_notificacao` - Quarto Notificação
- `event.cozinha_notificacao` - Cozinha Notificação
- `tts.google_translate_en_com` - Google Translate en com

---

## 🔧 Configuração Inicial

### Ver/Atualizar Configuração

**Endpoint:** `GET/POST /api/homeassistant/my_config/`

**Exemplo - Obter configuração:**
```bash
GET /api/homeassistant/my_config/
Authorization: Bearer <token>
```

**Exemplo - Atualizar configuração:**
```json
POST /api/homeassistant/my_config/
{
  "base_url": "http://192.168.1.100:8123",
  "long_lived_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "enabled": true
}
```

**Campos:**
- `base_url`: URL do Home Assistant (ex: `http://192.168.1.100:8123`)
- `long_lived_token`: Token de autenticação do Home Assistant
- `enabled`: Ativar/desativar integração (true/false)

---

## 📱 Visualizar Dispositivos

### Listar Todos os Dispositivos por Área

**Endpoint:** `GET /api/homeassistant/areas_and_devices/`

**Exemplo:**
```bash
GET /api/homeassistant/areas_and_devices/
Authorization: Bearer <token>
```

**Resposta:**
```json
{
  "areas": [
    {
      "id": "Cozinha",
      "name": "Cozinha",
      "devices": [
        {
          "entity_id": "climate.kitchen",
          "name": "Kitchen AC",
          "alias": "ar condicionado da cozinha",
          "area": "Cozinha",
          "domain": "climate",
          "state": "heat",
          "attributes": {
            "temperature": 22,
            "hvac_mode": "heat",
            "friendly_name": "Kitchen AC"
          }
        }
      ]
    }
  ],
  "no_area_devices": [
    {
      "entity_id": "sensor.outside_temperature",
      "name": "Outside Temperature",
      "domain": "sensor",
      "state": "18.5"
    }
  ]
}
```

**O que podes fazer:**
- Ver todos os dispositivos organizados por área/divisão
- Ver dispositivos sem área atribuída
- Ver estados atuais de cada dispositivo
- Ver atributos detalhados (temperatura, brilho, etc.)

---

## 🎮 Controlar Dispositivos

### Controlar Qualquer Dispositivo

**Endpoint:** `POST /api/homeassistant/control_device/`

**Formato geral:**
```json
{
  "entity_id": "domain.entity_name",
  "domain": "light|switch|climate|fan|cover|media_player|...",
  "service": "turn_on|turn_off|set_temperature|...",
  "data": {
    // Parâmetros específicos do serviço
  }
}
```

---

## 💡 Exemplos Práticos por Tipo de Dispositivo

### 1. Lâmpadas (Light)

#### Ligar uma lâmpada
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "light.living_room",
  "domain": "light",
  "service": "turn_on",
  "data": {
    "entity_id": "light.living_room"
  }
}
```

#### Ligar com brilho e cor
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "light.bedroom",
  "domain": "light",
  "service": "turn_on",
  "data": {
    "entity_id": "light.bedroom",
    "brightness": 255,
    "rgb_color": [255, 200, 150],
    "color_name": "warm"
  }
}
```

#### Desligar uma lâmpada
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "light.living_room",
  "domain": "light",
  "service": "turn_off",
  "data": {
    "entity_id": "light.living_room"
  }
}
```

#### Alternar estado (ligar/desligar)
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "light.kitchen",
  "domain": "light",
  "service": "toggle",
  "data": {
    "entity_id": "light.kitchen"
  }
}
```

### 2. Ar Condicionado / Climatização (Climate)

#### Definir temperatura
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.bedroom",
  "domain": "climate",
  "service": "set_temperature",
  "data": {
    "entity_id": "climate.bedroom",
    "temperature": 23,
    "hvac_mode": "cool"
  }
}
```

#### Modos disponíveis:
- `"heat"` - Aquecimento
- `"cool"` - Arrefecimento
- `"auto"` - Automático
- `"off"` - Desligado

#### Ligar ar condicionado em modo calor
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.living_room",
  "domain": "climate",
  "service": "set_temperature",
  "data": {
    "entity_id": "climate.living_room",
    "temperature": 22,
    "hvac_mode": "heat"
  }
}
```

#### Desligar ar condicionado
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.bedroom",
  "domain": "climate",
  "service": "set_hvac_mode",
  "data": {
    "entity_id": "climate.bedroom",
    "hvac_mode": "off"
  }
}
```

### 3. Interruptores (Switch)

#### Ligar interruptor
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.coffee_maker",
  "domain": "switch",
  "service": "turn_on",
  "data": {
    "entity_id": "switch.coffee_maker"
  }
}
```

#### Desligar interruptor
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.coffee_maker",
  "domain": "switch",
  "service": "turn_off",
  "data": {
    "entity_id": "switch.coffee_maker"
  }
}
```

### 4. Ventiladores (Fan)

#### Ligar ventilador
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "fan.bedroom",
  "domain": "fan",
  "service": "turn_on",
  "data": {
    "entity_id": "fan.bedroom",
    "speed": "medium"
  }
}
```

#### Definir velocidade
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "fan.living_room",
  "domain": "fan",
  "service": "set_speed",
  "data": {
    "entity_id": "fan.living_room",
    "speed": "high"
  }
}
```

**Velocidades disponíveis:** `"low"`, `"medium"`, `"high"`, `"off"`

### 5. Persianas / Cortinas (Cover)

#### Abrir persianas
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "cover.living_room_blinds",
  "domain": "cover",
  "service": "open_cover",
  "data": {
    "entity_id": "cover.living_room_blinds"
  }
}
```

#### Fechar persianas
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "cover.living_room_blinds",
  "domain": "cover",
  "service": "close_cover",
  "data": {
    "entity_id": "cover.living_room_blinds"
  }
}
```

#### Definir posição (0-100)
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "cover.bedroom_blinds",
  "domain": "cover",
  "service": "set_cover_position",
  "data": {
    "entity_id": "cover.bedroom_blinds",
    "position": 50
  }
}
```

### 6. Media Player

#### Reproduzir música
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "media_player.living_room",
  "domain": "media_player",
  "service": "play_media",
  "data": {
    "entity_id": "media_player.living_room",
    "media_content_id": "spotify:track:4iV5W9uYEdYUVa79Axb7Rh",
    "media_content_type": "music"
  }
}
```

#### Pausar
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "media_player.living_room",
  "domain": "media_player",
  "service": "media_pause",
  "data": {
    "entity_id": "media_player.living_room"
  }
}
```

#### Aumentar volume
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "media_player.living_room",
  "domain": "media_player",
  "service": "volume_up",
  "data": {
    "entity_id": "media_player.living_room"
  }
}
```

### 7. Sensores (Sensor)

**Nota:** Sensores são normalmente apenas de leitura. Para ver o estado atual, usa `GET /api/homeassistant/areas_and_devices/` ou consulta diretamente o estado.

---

## 🏷️ Gerir Aliases

Os aliases permitem atribuir nomes amigáveis aos dispositivos para facilitar o controlo por voz.

### Listar Aliases

**Endpoint:** `GET /api/device-aliases/`

**Exemplo:**
```bash
GET /api/device-aliases/
Authorization: Bearer <token>
```

**Resposta:**
```json
[
  {
    "id": 1,
    "entity_id": "climate.kitchen",
    "alias": "ar condicionado da cozinha",
    "area": "Cozinha"
  },
  {
    "id": 2,
    "entity_id": "light.bedroom",
    "alias": "luz do quarto",
    "area": "Quarto"
  }
]
```

### Criar Alias

**Endpoint:** `POST /api/device-aliases/`

**Exemplo:**
```json
POST /api/device-aliases/
{
  "entity_id": "climate.bedroom",
  "alias": "ar condicionado do quarto",
  "area": "Quarto"
}
```

**Campos:**
- `entity_id`: ID da entidade do Home Assistant (obrigatório)
- `alias`: Nome amigável para o dispositivo (obrigatório)
- `area`: Nome da área/divisão (opcional)

### Atualizar Alias

**Endpoint:** `PATCH /api/device-aliases/{id}/`

**Exemplo:**
```json
PATCH /api/device-aliases/1/
{
  "alias": "ar condicionado principal da cozinha",
  "area": "Cozinha"
}
```

### Eliminar Alias

**Endpoint:** `DELETE /api/device-aliases/{id}/`

**Exemplo:**
```bash
DELETE /api/device-aliases/1/
Authorization: Bearer <token>
```

---

## 🔌 Endpoints da API - Referência Completa

### Configuração

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/homeassistant/my_config/` | Obter configuração do utilizador |
| POST | `/api/homeassistant/my_config/` | Criar/atualizar configuração |

### Dispositivos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/homeassistant/areas_and_devices/` | Listar dispositivos por área |
| POST | `/api/homeassistant/control_device/` | Controlar um dispositivo |

### Aliases

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/device-aliases/` | Listar todos os aliases |
| POST | `/api/device-aliases/` | Criar novo alias |
| GET | `/api/device-aliases/{id}/` | Obter alias específico |
| PATCH | `/api/device-aliases/{id}/` | Atualizar alias |
| DELETE | `/api/device-aliases/{id}/` | Eliminar alias |

---

## 🏠 Exemplos Práticos com os Teus Dispositivos

Baseado nos dispositivos que tens configurados no Home Assistant, aqui estão exemplos práticos específicos:

### Ar Condicionados (Climate)

Tens 3 ar condicionados: **Sala**, **Quarto**, e **Cozinha**.

#### Ajustar temperatura da Sala
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.sala",
  "domain": "climate",
  "service": "set_temperature",
  "data": {
    "entity_id": "climate.sala",
    "temperature": 23,
    "hvac_mode": "heat"
  }
}
```

#### Ajustar temperatura do Quarto
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.quarto",
  "domain": "climate",
  "service": "set_temperature",
  "data": {
    "entity_id": "climate.quarto",
    "temperature": 22,
    "hvac_mode": "cool"
  }
}
```

#### Ligar ar condicionado da Cozinha
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.cozinha",
  "domain": "climate",
  "service": "set_temperature",
  "data": {
    "entity_id": "climate.cozinha",
    "temperature": 21,
    "hvac_mode": "heat"
  }
}
```

#### Desligar ar condicionado da Sala
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.sala",
  "domain": "climate",
  "service": "set_hvac_mode",
  "data": {
    "entity_id": "climate.sala",
    "hvac_mode": "off"
  }
}
```

### Interruptores (Switch)

Tens interruptores para ligar/desligar e poupança de energia em cada divisão.

#### Ligar AC da Sala
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.sala_ligar_desligar",
  "domain": "switch",
  "service": "turn_on",
  "data": {
    "entity_id": "switch.sala_ligar_desligar"
  }
}
```

#### Desligar AC da Sala
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.sala_ligar_desligar",
  "domain": "switch",
  "service": "turn_off",
  "data": {
    "entity_id": "switch.sala_ligar_desligar"
  }
}
```

#### Ativar poupança de energia no Quarto
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.quarto_poupanca_de_energia",
  "domain": "switch",
  "service": "turn_on",
  "data": {
    "entity_id": "switch.quarto_poupanca_de_energia"
  }
}
```

#### Desativar poupança de energia na Cozinha
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.cozinha_poupanca_de_energia",
  "domain": "switch",
  "service": "turn_off",
  "data": {
    "entity_id": "switch.cozinha_poupanca_de_energia"
  }
}
```

### Media Players

Tens vários media players: MEOBox 4K, Mi TV, e Hisense VIDAA TV.

#### Controlar Pen de transmissão Mi TV
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "media_player.pen_de_transmissao_mi_tv",
  "domain": "media_player",
  "service": "turn_on",
  "data": {
    "entity_id": "media_player.pen_de_transmissao_mi_tv"
  }
}
```

#### Desligar Mi TV
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "media_player.pen_de_transmissao_mi_tv",
  "domain": "media_player",
  "service": "turn_off",
  "data": {
    "entity_id": "media_player.pen_de_transmissao_mi_tv"
  }
}
```

#### Reproduzir conteúdo no MEOBox
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "media_player.meobox_4k_diw377",
  "domain": "media_player",
  "service": "play_media",
  "data": {
    "entity_id": "media_player.meobox_4k_diw377",
    "media_content_id": "canal_123",
    "media_content_type": "channel"
  }
}
```

### Remote Control

#### Controlar remoto da Mi TV
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "remote.pen_de_transmissao_mi_tv",
  "domain": "remote",
  "service": "turn_on",
  "data": {
    "entity_id": "remote.pen_de_transmissao_mi_tv"
  }
}
```

### Sensores (Apenas Leitura)

Estes dispositivos são apenas de leitura, mas podes consultar os seus estados:

- **Sun sensors**: `sensor.sun_next_dawn`, `sensor.sun_next_dusk`, etc.
- **Backup sensors**: `sensor.backup_backup_manager_state`, `sensor.backup_next_scheduled_automatic_backup`
- **Weather**: `weather.forecast_inicio`
- **Programação sensors**: `sensor.sala_programar_a_ligar`, `sensor.quarto_programar_desligar`, etc.

Para ver os estados, usa:
```bash
GET /api/homeassistant/areas_and_devices/
```

### Numbers (Valores Configuráveis)

Tens números configuráveis para programação e temporizadores:

#### Definir hora de ligar AC da Sala
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "number.sala_programar_a_ligar",
  "domain": "number",
  "service": "set_value",
  "data": {
    "entity_id": "number.sala_programar_a_ligar",
    "value": 8.5
  }
}
```

#### Definir temporizador de sono do Quarto
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "number.quarto_temporizador_de_sono",
  "domain": "number",
  "service": "set_value",
  "data": {
    "entity_id": "number.quarto_temporizador_de_sono",
    "value": 60
  }
}
```

### Todo List

#### Adicionar item à lista de compras
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "todo.lista_de_compras",
  "domain": "todo",
  "service": "add_item",
  "data": {
    "entity_id": "todo.lista_de_compras",
    "item": "Leite"
  }
}
```

#### Completar item da lista
```json
POST /api/homeassistant/control_device/
{
  "entity_id": "todo.lista_de_compras",
  "domain": "todo",
  "service": "update_item",
  "data": {
    "entity_id": "todo.lista_de_compras",
    "item": "Leite",
    "status": "completed"
  }
}
```

### Aliases Recomendados

Para facilitar o controlo por voz, podes criar aliases:

```json
POST /api/device-aliases/
{
  "entity_id": "climate.sala",
  "alias": "ar condicionado da sala",
  "area": "Sala"
}
```

```json
POST /api/device-aliases/
{
  "entity_id": "climate.quarto",
  "alias": "ar condicionado do quarto",
  "area": "Quarto"
}
```

```json
POST /api/device-aliases/
{
  "entity_id": "climate.cozinha",
  "alias": "ar condicionado da cozinha",
  "area": "Cozinha"
}
```

```json
POST /api/device-aliases/
{
  "entity_id": "switch.sala_ligar_desligar",
  "alias": "ligar ar condicionado da sala",
  "area": "Sala"
}
```

```json
POST /api/device-aliases/
{
  "entity_id": "media_player.pen_de_transmissao_mi_tv",
  "alias": "televisão",
  "area": "Sala"
}
```

## 🎯 Casos de Uso Comuns

### Cenário 1: Acordar de Manhã
```json
// 1. Ligar ar condicionado da Sala
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.sala_ligar_desligar",
  "domain": "switch",
  "service": "turn_on",
  "data": {}
}

// 2. Ajustar temperatura da Sala para conforto
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.sala",
  "domain": "climate",
  "service": "set_temperature",
  "data": {
    "temperature": 22,
    "hvac_mode": "heat"
  }
}

// 3. Ligar ar condicionado do Quarto
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.quarto_ligar_desligar",
  "domain": "switch",
  "service": "turn_on",
  "data": {}
}
```

### Cenário 2: Preparar para Dormir
```json
// 1. Ajustar temperatura do Quarto para dormir
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.quarto",
  "domain": "climate",
  "service": "set_temperature",
  "data": {
    "temperature": 20,
    "hvac_mode": "heat"
  }
}

// 2. Ativar poupança de energia no Quarto
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.quarto_poupanca_de_energia",
  "domain": "switch",
  "service": "turn_on",
  "data": {}
}

// 3. Desligar ar condicionado da Sala
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.sala_ligar_desligar",
  "domain": "switch",
  "service": "turn_off",
  "data": {}
}

// 4. Desligar televisão
POST /api/homeassistant/control_device/
{
  "entity_id": "media_player.pen_de_transmissao_mi_tv",
  "domain": "media_player",
  "service": "turn_off",
  "data": {}
}
```

### Cenário 3: Ambiente de Trabalho / Estar em Casa
```json
// 1. Ligar ar condicionado da Sala
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.sala_ligar_desligar",
  "domain": "switch",
  "service": "turn_on",
  "data": {}
}

// 2. Ajustar temperatura da Sala para conforto
POST /api/homeassistant/control_device/
{
  "entity_id": "climate.sala",
  "domain": "climate",
  "service": "set_temperature",
  "data": {
    "temperature": 22,
    "hvac_mode": "cool"
  }
}

// 3. Ligar televisão se necessário
POST /api/homeassistant/control_device/
{
  "entity_id": "media_player.pen_de_transmissao_mi_tv",
  "domain": "media_player",
  "service": "turn_on",
  "data": {}
}
```

### Cenário 4: Economizar Energia
```json
// 1. Ativar poupança de energia em todas as divisões
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.sala_poupanca_de_energia",
  "domain": "switch",
  "service": "turn_on",
  "data": {}
}

POST /api/homeassistant/control_device/
{
  "entity_id": "switch.quarto_poupanca_de_energia",
  "domain": "switch",
  "service": "turn_on",
  "data": {}
}

POST /api/homeassistant/control_device/
{
  "entity_id": "switch.cozinha_poupanca_de_energia",
  "domain": "switch",
  "service": "turn_on",
  "data": {}
}

// 2. Desligar ar condicionado da Cozinha se não estiver em uso
POST /api/homeassistant/control_device/
{
  "entity_id": "switch.cozinha_ligar_desligar",
  "domain": "switch",
  "service": "turn_off",
  "data": {}
}
```

### Cenário 5: Configurar Programação Automática
```json
// 1. Programar AC da Sala para ligar às 7h da manhã
POST /api/homeassistant/control_device/
{
  "entity_id": "number.sala_programar_a_ligar",
  "domain": "number",
  "service": "set_value",
  "data": {
    "value": 7.0
  }
}

// 2. Programar AC do Quarto para desligar às 23h
POST /api/homeassistant/control_device/
{
  "entity_id": "number.quarto_programar_desligar",
  "domain": "number",
  "service": "set_value",
  "data": {
    "value": 23.0
  }
}

// 3. Definir temporizador de sono do Quarto para 60 minutos
POST /api/homeassistant/control_device/
{
  "entity_id": "number.quarto_temporizador_de_sono",
  "domain": "number",
  "service": "set_value",
  "data": {
    "value": 60
  }
}
```

---

## 🔍 Verificar Estados

Para verificar o estado atual de todos os dispositivos antes de fazer alterações:

```bash
GET /api/homeassistant/areas_and_devices/
```

Isto retorna:
- Estado atual de cada dispositivo (`on`, `off`, `heat`, `cool`, etc.)
- Atributos (temperatura, brilho, posição, etc.)
- Organização por área
- Aliases configurados

---

## ⚠️ Notas Importantes

1. **Autenticação:** Todos os endpoints requerem autenticação JWT via header `Authorization: Bearer <token>`

2. **Entity IDs:** Os `entity_id` devem corresponder exatamente aos IDs das entidades no Home Assistant (ex: `light.living_room`, `climate.bedroom`)

3. **Domínios Suportados:** A interface suporta controlo direto para:
   - `light` - Lâmpadas
   - `switch` - Interruptores
   - `climate` - Ar condicionado/Climatização
   - `fan` - Ventiladores
   - `cover` - Persianas/Cortinas
   - `media_player` - Media players

4. **Outros Domínios:** Outros domínios podem ser controlados via API, mas podem não ter interface visual na página Home Assistant

5. **Aliases:** Os aliases são úteis para:
   - Controlo por voz através do assistente
   - Organização visual na interface
   - Identificação rápida de dispositivos

---

## 🚀 Integração com Assistente de Voz

Os aliases configurados permitem controlar dispositivos através do assistente de voz usando comandos naturais como:

- "Liga a luz da sala"
- "Aumenta a temperatura do ar condicionado para 24 graus"
- "Desliga o interruptor da cozinha"
- "Abre as persianas do quarto"

O assistente usa os aliases para identificar os dispositivos e chama automaticamente os serviços apropriados do Home Assistant.

---

## 📝 Exemplo Completo: Fluxo de Trabalho

1. **Configurar Home Assistant:**
   ```json
   POST /api/homeassistant/my_config/
   {
     "base_url": "http://192.168.1.100:8123",
     "long_lived_token": "seu_token_aqui",
     "enabled": true
   }
   ```

2. **Ver dispositivos disponíveis:**
   ```bash
   GET /api/homeassistant/areas_and_devices/
   ```

3. **Criar aliases para facilitar:**
   ```json
   POST /api/device-aliases/
   {
     "entity_id": "light.living_room",
     "alias": "luz da sala",
     "area": "Sala"
   }
   ```

4. **Controlar dispositivos:**
   ```json
   POST /api/homeassistant/control_device/
   {
     "entity_id": "light.living_room",
     "domain": "light",
     "service": "turn_on",
     "data": { "brightness": 255 }
   }
   ```

5. **Verificar resultado:**
   ```bash
   GET /api/homeassistant/areas_and_devices/
   ```

---

## 🔗 Recursos Adicionais

- **Home Assistant API Documentation:** https://developers.home-assistant.io/docs/api/rest/
- **Testar configuração:** Executar `python test_ha_config.py` no backend
- **Listar endpoints disponíveis:** Executar `python test_ha_endpoints.py` no backend

---

**Última atualização:** Baseado na interface `HomeAssistant.tsx` e endpoints disponíveis no backend.

