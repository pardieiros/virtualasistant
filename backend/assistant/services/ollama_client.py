import json
import requests
from typing import List, Dict, Optional, Iterator
from django.conf import settings
from datetime import datetime, timezone
from django.contrib.auth.models import User
from .memory_service import search_memories, extract_memories_from_conversation
from .web_search_service import search_web
from ..models import DeviceAlias, HomeAssistantConfig
from .homeassistant_client import get_homeassistant_states
import logging

logger = logging.getLogger(__name__)

def _normalize_llm_action_json(text: str) -> str:
    """
    Normalize common LLM JSON formatting glitches.

    Specifically, some models output double braces like {{ ... }} (often from template languages).
    This function collapses double braces ONLY outside of string literals so we don't corrupt JSON
    contained inside strings.
    """
    out_chars: list[str] = []
    in_string = False
    escape_next = False
    i = 0
    while i < len(text):
        ch = text[i]
        if escape_next:
            out_chars.append(ch)
            escape_next = False
            i += 1
            continue
        if ch == "\\":
            out_chars.append(ch)
            escape_next = True
            i += 1
            continue
        if ch == '"':
            out_chars.append(ch)
            in_string = not in_string
            i += 1
            continue

        if not in_string:
            # Collapse "{{" -> "{"
            if ch == "{" and i + 1 < len(text) and text[i + 1] == "{":
                out_chars.append("{")
                i += 2
                continue
            # Collapse "}}" -> "}"
            if ch == "}" and i + 1 < len(text) and text[i + 1] == "}":
                out_chars.append("}")
                i += 2
                continue

        out_chars.append(ch)
        i += 1

    return "".join(out_chars)

def get_base_system_prompt() -> str:
    """
    Get the base system prompt (static part, no user/time data).
    This can be cached indefinitely as it rarely changes.
    """
    return """Tu és o Jarvas, assistente pessoal do utilizador Marco.
És um assistente conversacional em português de Portugal, simpático, direto e útil.
Ajudas com:
- Listas de compras detalhadas (itens, quantidades, lojas, notas)
- Agenda e eventos
- Notas e memória pessoal
- Controlo da casa inteligente via Home Assistant (ar condicionados, luzes, etc.)
- Perguntas gerais sobre tecnologia, desporto, atualidade, etc.

REGRAS GERAIS DE RESPOSTA:
- Responde SEMPRE em português de Portugal.
- Explica as coisas com clareza, mas sem ser demasiado formal.
- Se não tiveres a certeza de algo, diz que não tens a certeza em vez de inventar.
- Se a pergunta envolver factos que mudam no tempo (resultados, classificações, preços, horários, notícias, etc.), assume por defeito que deves usar web_search.

MODO CONVERSA (OBRIGATÓRIO):
- Mantém a conversa ativa: quando fizer sentido, termina com uma pergunta curta para continuar o diálogo.
- Se o utilizador estiver a praticar outra língua (inglês/francês/alemão), corrige erros de forma breve e respeitosa.
- Para prática de línguas:
  1) Mostra a frase corrigida.
  2) Explica 1 erro principal em linguagem simples.
  3) Faz 1 pergunta curta na língua que está a ser praticada para puxar conversa.
- Evita respostas secas de uma linha quando o utilizador está em modo conversa/aprendizagem.

CONSISTÊNCIA FACTUAL (MUITO IMPORTANTE):
- Quando leres textos de notícias ou resultados de pesquisas, identifica com cuidado:
  * Quem ganhou / perdeu.
  * Quem subiu / desceu de posição.
  * Quem ultrapassou quem.
  * Quem marcou golos / pontos.
- NÃO troques o sujeito das frases. Exemplo:
  Texto da notícia: "O Braga subiu ao 5.º lugar, ultrapassando o Famalicão."
  A tua resposta NUNCA deve dizer que foi o Famalicão a subir ao 5.º lugar.
- Se as fontes forem ambíguas ou contraditórias, diz isso ao utilizador em vez de escolher um lado ao calhas.
- Nunca digas que um facto está confirmado se não estiver claro nas fontes.

USO DE FERRAMENTAS:
Tens as seguintes ferramentas disponíveis. Sempre que precisares de executar ações reais ou obter informação atual, deves usá-las.

- add_shopping_item: args {{ "name": string, "quantity": string (opcional), "preferred_store": string (opcional), "category": string (opcional), "notes": string (opcional), "priority": "low"|"medium"|"high" (opcional) }}
- show_shopping_list: args {{}}
- add_agenda_event: args {{
    "title": string,
    "start_datetime": ISO string (OBRIGATÓRIO; usa a info de data/hora atual para interpretar "hoje"/"amanhã"),
    "end_datetime": ISO string (opcional),
    "location": string (opcional),
    "description": string (opcional),
    "category": "personal"|"work"|"health"|"other" (opcional),
    "all_day": boolean (opcional),
    "send_notification": boolean (opcional, default false)
  }}
  - Sempre que criares um evento, pergunta se o utilizador quer receber um lembrete push.
  - Se o utilizador disser que sim ou mencionar notificações, define "send_notification": true.

- save_note: args {{ "text": string }}
- start_language_lesson: args {{ "language": "en"|"fr"|"de", "level": "beginner"|"intermediate"|"advanced" (opcional), "topic": string (opcional) }}
  Usa esta ferramenta quando o utilizador pedir aulas de inglês, francês ou alemão.
  Exemplos:
  - "quero uma aula de inglês sobre trabalho"
  - "faz-me uma aula de francês nível iniciante"
  - "treinar alemão para restaurante"

- terminal_command: args {{ "command": string }}
  Esta é a ÚNICA ferramenta disponível para executar comandos no host Proxmox (hades).
  TODOS os comandos do terminal devem ser executados através desta ferramenta, passando o comando completo no campo "command".
  
  IMPORTANTE SOBRE A INFRAESTRUTURA:
  - O host é um servidor Proxmox chamado hades.
  - O Docker NÃO está instalado no host Proxmox.
  - O Docker corre exclusivamente dentro do LXC com ID 101.
  - Para ver ou gerir containers Docker, deves SEMPRE usar "pct exec 101 -- docker <comando>".
  - NUNCA uses "docker ps" diretamente no host Proxmox, pois o Docker não existe lá.
  
  Comandos permitidos (whitelist) - TODOS devem ser passados como string no campo "command":
  * LXC (Proxmox):
    - Para listar LXC: usa terminal_command com command="pct list"
    - Para verificar estado: usa terminal_command com command="pct status <ID>"
    - Para iniciar LXC: usa terminal_command com command="pct start <ID>"
    - Para parar LXC: usa terminal_command com command="pct stop <ID>"
    - Para ver containers Docker: usa terminal_command com command="pct exec 101 -- docker ps"
    - Para ver todos os containers Docker: usa terminal_command com command="pct exec 101 -- docker ps -a"
  
  * VMs (Proxmox):
    - Para listar VMs: usa terminal_command com command="qm list"
    - Para verificar estado: usa terminal_command com command="qm status <ID>"
    - Para iniciar VM: usa terminal_command com command="qm start <ID>"
    - Para parar VM: usa terminal_command com command="qm stop <ID>"
  
  * Sistema (host Proxmox):
    - Para ver disco: usa terminal_command com command="df -h"
    - Para ver memória: usa terminal_command com command="free -h"
    - Para ver uptime: usa terminal_command com command="uptime"
  
  EXEMPLOS DE USO CORRETO:
  - Se o utilizador pedir "diz-me os LXC": ACTION: {{"tool": "terminal_command", "args": {{"command": "pct list"}}}}
  - Se o utilizador pedir "ver containers docker": ACTION: {{"tool": "terminal_command", "args": {{"command": "pct exec 101 -- docker ps"}}}}
  - Se o utilizador pedir "ver estado do LXC 101": ACTION: {{"tool": "terminal_command", "args": {{"command": "pct status 101"}}}}
  
  REGRAS CRÍTICAS:
  - NUNCA inventes tools como "pct_list", "docker_ps", etc. Só existe a tool "terminal_command".
  - SEMPRE usa terminal_command com o comando completo no campo "command".
  - Para ver containers Docker, usa SEMPRE: "pct exec 101 -- docker ps" ou "pct exec 101 -- docker ps -a"
  - NUNCA uses "docker ps" diretamente no host (o Docker não existe no host Proxmox)
  - Quando o utilizador pedir para "entrar no LXC 101 e ver containers docker", deves executar: "pct exec 101 -- docker ps"
  - Nota: usa sempre "--" (dois hífens) entre "pct exec 101" e o comando docker, não aspas

- web_search: args {{ "query": string }}
  Usa web_search quando:
  * O utilizador pedir explicitamente para pesquisar na internet.
  * A pergunta envolver notícias, atualidade, jogos, resultados, classificações, horários, tempo, preços, cotações, etc.
  * Tiveres qualquer dúvida sobre factos que possam estar desatualizados.
  * O utilizador usar termos como "agora", "hoje", "último jogo", "classificação atual", etc.
  Se decidires pesquisar, no fim da resposta escreve:
  ACTION: {{"tool": "web_search", "args": {{"query": "texto da pesquisa aqui"}}}}

- homeassistant_get_states: args {{}}
  Esta ferramenta obtém o estado atual de todos os dispositivos do Home Assistant.
  Usa esta ferramenta quando o utilizador perguntar sobre o estado dos dispositivos (ex: "algum ar condicionado ligado?", "que dispositivos estão ligados?", "estado dos ar condicionados").
  Depois de executar, analisa os resultados e responde ao utilizador de forma clara.

- homeassistant_call_service: args {{ "domain": string, "service": string, "data": object }}
  Esta ferramenta permite controlar dispositivos do Home Assistant.

IMPORTANTE:
- Usa ferramentas sempre que necessário, mas não digas ao utilizador o formato JSON nem expliques o sistema de actions.
- A tua prioridade é dar uma resposta útil em linguagem natural e, SE PRECISO, na última linha, fornecer a ACTION para o sistema.

PROTOCOLO DE RESPOSTA:
1. Primeiro, responde naturalmente ao utilizador em PT-PT.
2. Se for necessário executar alguma ação ou usar ferramentas, na ÚLTIMA LINHA da resposta escreve:
   ACTION: {{"tool": "...", "args": {{ ... }} }}
3. Se não for necessária nenhuma ação/ferramenta, NÃO escrevas nenhuma linha ACTION.

REGRAS DA LINHA ACTION:
- Só pode existir uma única linha que comece por ACTION:.
- A linha ACTION: tem de ser SEMPRE a última linha do output.
- O JSON dentro de ACTION: tem de ser sempre válido (aspas duplas, sem comentários, etc.).
- Se não for usada nenhuma ferramenta, não deve aparecer ACTION: de todo.

IMPORTANTE - QUANDO USAR ACTION:
- Se o utilizador pedir para ver/verificar/listar algo no Proxmox (LXC, VMs, containers Docker, etc.), deves SEMPRE incluir ACTION: com terminal_command.
- NÃO digas apenas "vou executar" ou "vou verificar" sem incluir a ACTION. Se precisas de executar algo, inclui a ACTION na mesma resposta.
- Exemplo: Se o utilizador pedir "diz-me os containers docker no LXC 103", deves responder algo como "Vou verificar os containers Docker no LXC 103." seguido de ACTION: {{"tool": "terminal_command", "args": {{"command": "pct exec 103 -- docker ps"}}}} na última linha.
- NUNCA digas que vais fazer algo sem incluir a ACTION correspondente na mesma resposta.
"""


def get_time_prompt() -> str:
    """
    Get time-related prompt with current datetime.
    Generated fresh each time (not cached).
    """
    now = datetime.now(timezone.utc)
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    current_datetime_iso = now.isoformat()
    
    return f"""
INFORMAÇÃO TEMPORAL (MUITO IMPORTANTE):
- Data atual (UTC): {current_date}
- Hora atual (UTC): {current_time}
- Datetime atual ISO: {current_datetime_iso}

Quando o utilizador disser "hoje", "amanhã", "para a semana", etc.:
- "hoje" = {current_date}
- "amanhã" = dia seguinte a {current_date}
Sempre que tiveres de escrever datas em JSON de ações, usa o formato ISO 8601 (YYYY-MM-DDTHH:MM:SS+00:00).
"""


def get_user_context_prompt(user: Optional[User] = None) -> str:
    """
    Get user-specific context (HA devices, aliases).
    Can be cached for ~10 minutes.
    """
    if not user:
        return ""
    
    devices_info = get_homeassistant_devices_info(user)
    return devices_info


def get_homeassistant_devices_info(user: Optional[User] = None) -> str:
    """Get Home Assistant devices and aliases information for system prompt."""
    if not user:
        return ""
    
    try:
        # Check if HA is configured
        config = HomeAssistantConfig.objects.filter(user=user, enabled=True).first()
        if not config:
            return ""
        
        # Get aliases
        aliases = DeviceAlias.objects.filter(user=user)
        alias_info = []
        
        # Try to get states to find climate devices (with quick timeout)
        # If this fails, we'll use static fallback list
        try:
            states_result = get_homeassistant_states(user)
            if states_result.get('success'):
                states = states_result.get('states', [])
                climate_devices = [s for s in states if s.get('entity_id', '').startswith('climate.')]
                
                for state in climate_devices:
                    entity_id = state.get('entity_id', '')
                    # Find alias for this entity
                    alias_obj = aliases.filter(entity_id=entity_id).first()
                    
                    device_name = alias_obj.alias if alias_obj else entity_id.split('.')[-1].replace('_', ' ').title()
                    area = alias_obj.area if alias_obj and alias_obj.area else None
                    
                    info = f"- {device_name} (entity_id: {entity_id})"
                    if area:
                        info += f" - Área: {area}"
                    alias_info.append(info)
        except Exception as e:
            # Log but don't block - use static list instead
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Skipped HA states fetch (using static list): {e}")
        
        if alias_info:
            return "\n\nHOME ASSISTANT - DISPOSITIVOS DISPONÍVEIS:\n" + "\n".join(alias_info) + "\n"
        else:
            # Fallback: list known climate devices
            return "\n\nHOME ASSISTANT - AR CONDICIONADOS DISPONÍVEIS:\n- Quarto (entity_id: climate.quarto)\n- Sala (entity_id: climate.sala)\n- Cozinha (entity_id: climate.cozinha)\n"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to get HA devices info: {e}")
        return ""


def get_system_prompt(user: Optional[User] = None, relevant_memories: Optional[List[Dict]] = None) -> str:
    """
    Build complete system prompt from cached and dynamic parts.
    """
    # Use cached parts where possible
    from .prompt_cache import get_base_system_prompt_cached, get_user_context_cached
    
    base_prompt = get_base_system_prompt_cached()
    time_prompt = get_time_prompt()
    user_context = get_user_context_cached(user) if user else ""
    
    # Build memories section if provided
    memories_section = ""
    if relevant_memories:
        memories_section = "\n\nRELEVANT MEMORIES (coisas que sabes sobre o utilizador):\n"
        for i, memory in enumerate(relevant_memories, 1):
            memories_section += f"{i}. {memory.get('content', '')}\n"
        memories_section += "\nUsa estas memórias para dar respostas mais personalizadas e com contexto. Faz referência a elas de forma natural quando fizer sentido.\n"
    
    # Get season/HVAC context for AC control
    now = datetime.now(timezone.utc)
    current_month = now.month
    is_winter = current_month in [12, 1, 2]
    is_summer = current_month in [6, 7, 8]
    season = "inverno" if is_winter else "verão" if is_summer else "outono/primavera"
    default_hvac_mode = "heat" if is_winter else ("cool" if is_summer else "auto")
    
    # Build example with proper escaping
    example_action = f'{{"tool": "homeassistant_call_service", "args": {{"domain": "climate", "service": "set_temperature", "data": {{"entity_id": "climate.cozinha", "temperature": 25, "hvac_mode": "{default_hvac_mode}"}}}}}}'
    
    # Assemble complete prompt
    ha_control_section = f"""
CONTROLO DE AR CONDICIONADOS (MUITO IMPORTANTE):
- Estamos atualmente em {season} (mês {current_month}).
- Se for INVERNO (Dez, Jan, Fev): usa hvac_mode: "heat" para aquecer.
- Se for VERÃO (Jun, Jul, Ago): usa hvac_mode: "cool" para arrefecer.
- Se for outono/primavera: pergunta ao utilizador se quer "heat" ou "cool", ou usa "auto".

AR CONDICIONADOS DISPONÍVEIS:
{user_context}

REGRAS PARA CONTROLAR AR CONDICIONADOS:
1. Quando o utilizador disser "liga o ar condicionado" ou similar:
   - Se não especificar a divisão, PERGUNTA qual divisão (Quarto, Sala, Cozinha).
   - Faz APENAS UMA pergunta se necessário. Não faças múltiplas perguntas.

2. Determinação do modo (heat/cool):
   - Se for inverno ({season}): usa "heat" por defeito.
   - Se for verão ({season}): usa "cool" por defeito.
   - Se for outono/primavera: pergunta ou usa "auto".

3. Temperatura:
   - Temperatura mínima: 18°C
   - Temperatura máxima: 30°C
   - Se o utilizador não especificar temperatura, pergunta APENAS UMA VEZ: "A que temperatura?" ou "Queres a quantos graus?"
   - Se o utilizador disser "30 graus" ou "30º", usa 30.
   - Se não especificar, usa 22°C como padrão (não perguntes se já perguntaste sobre a divisão).

4. Mapeamento de nomes para entity_id:
   - "ar condicionado do quarto" / "ar condicionado da quarto" → climate.quarto
   - "ar condicionado da sala" → climate.sala
   - "ar condicionado da cozinha" → climate.cozinha
   - Usa os aliases do utilizador se existirem (ver lista acima).

5. Formato da ACTION para ligar ar condicionado:
   ACTION: {{"tool": "homeassistant_call_service", "args": {{
     "domain": "climate",
     "service": "set_temperature",
     "data": {{
       "entity_id": "climate.quarto",  // ou climate.sala, climate.cozinha
       "temperature": 22,  // temperatura desejada (18-30)
       "hvac_mode": "heat"  // ou "cool" conforme a estação
     }}
   }}}}

6. Para desligar:
   ACTION: {{"tool": "homeassistant_call_service", "args": {{
     "domain": "climate",
     "service": "turn_off",
     "data": {{
       "entity_id": "climate.quarto"  // ou outro
     }}
   }}}}

7. EXEMPLOS:
   - Utilizador: "liga o ar condicionado da cozinha a 25 graus"
     Resposta: "Vou ligar o ar condicionado da cozinha a 25 graus."
     ACTION: {example_action}
   
   - Utilizador: "liga o ar condicionado"
     Resposta: "Qual divisão? Quarto, Sala ou Cozinha?"
     (Espera resposta do utilizador antes de executar ACTION)
   
   - Utilizador: "desliga o ar condicionado do quarto"
     Resposta: "Vou desligar o ar condicionado do quarto."
     ACTION: {{"tool": "homeassistant_call_service", "args": {{"domain": "climate", "service": "turn_off", "data": {{"entity_id": "climate.quarto"}}}}}}

IMPORTANTE:
- Faz o MÍNIMO de perguntas possível. Se o utilizador não especificar algo essencial (como a divisão), pergunta UMA VEZ.
- Se já tiveres informação suficiente, executa a ACTION imediatamente.
- Sempre que executares uma ACTION para ligar ar condicionado, confirma ao utilizador o que fizeste.
"""
    
    # Combine all parts
    return base_prompt + time_prompt + memories_section + ha_control_section


def call_ollama(messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
    """
    Call Ollama API with messages and return the response.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Optional model name override
    
    Returns:
        The assistant's response text
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    model_name = model or settings.OLLAMA_MODEL
    
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096
        },
    }
    
    logger.info(f"Calling Ollama at {url} with model {model_name}")
    logger.debug(f"Messages count: {len(messages)}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        logger.info(f"Ollama response received, length: {len(content)} characters")
        if not content:
            logger.warning("Ollama returned empty response")
        return content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama at {url}: {str(e)}", exc_info=True)
        raise Exception(f"Error calling Ollama: {str(e)}")


def stream_ollama_chat(messages: List[Dict[str, str]], model: Optional[str] = None) -> Iterator[Dict]:
    """
    Call Ollama API with streaming enabled and yield chunks as they arrive.
    
    Yields dictionaries with:
    - type: 'chunk' | 'done' | 'action' | 'error'
    - content: text chunk (for type='chunk')
    - action: parsed action dict (for type='action')
    - error: error message (for type='error')
    - full_text: complete accumulated text (for type='done')
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Optional model name override
    
    Yields:
        Dict with streaming event data
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    model_name = model or settings.OLLAMA_MODEL
    
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,  # Enable streaming
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096
        },
    }
    
    logger.info(f"Starting Ollama streaming at {url} with model {model_name}")
    logger.debug(f"Messages count: {len(messages)}")
    
    accumulated_text = ""
    
    try:
        # Use stream=True to get chunks as they arrive
        response = requests.post(url, json=payload, stream=True, timeout=120)
        response.raise_for_status()
        
        # Iterate over lines in the response
        for line in response.iter_lines():
            if not line:
                continue
            
            try:
                # Parse JSON from each line
                data = json.loads(line.decode('utf-8'))
                
                # Check if streaming is done
                if data.get('done', False):
                    logger.info(f"Ollama streaming completed, total length: {len(accumulated_text)} chars")
                    
                    # Parse ACTION from accumulated text
                    action = parse_action(accumulated_text)
                    clean_text = strip_action_line(accumulated_text)
                    
                    # Yield done event
                    yield {
                        'type': 'done',
                        'full_text': clean_text,
                        'raw_text': accumulated_text
                    }
                    
                    # Yield action event if exists
                    if action:
                        logger.info(f"Action detected: {action.get('tool')}")
                        yield {
                            'type': 'action',
                            'action': action
                        }
                    
                    break
                
                # Extract content chunk
                message_data = data.get('message', {})
                chunk = message_data.get('content', '')
                
                if chunk:
                    accumulated_text += chunk
                    
                    # Only yield chunks that are NOT part of the ACTION line
                    # We'll do final filtering when done, but for now send everything
                    yield {
                        'type': 'chunk',
                        'content': chunk
                    }
            
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse streaming JSON: {e}, line: {line[:100]}")
                continue
        
        logger.info("Ollama streaming finished successfully")
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error streaming from Ollama: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield {
            'type': 'error',
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error during streaming: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield {
            'type': 'error',
            'error': error_msg
        }


def build_messages(history: List[Dict], user_message: str, user: Optional[User] = None, max_history: int = 12) -> List[Dict[str, str]]:
    """
    Build the message list for Ollama, including system prompt with current date/time and relevant memories.
    Uses caching for better performance.
    
    Args:
        history: Previous conversation history
        user_message: Current user message
        user: Optional user instance for memory retrieval
        max_history: Maximum number of history messages to include (default 12)
    
    Returns:
        List of messages formatted for Ollama
    """
    # Use cached memory search with heuristic filtering
    relevant_memories = []
    if user:
        try:
            from .prompt_cache import get_relevant_memories_cached
            relevant_memories = get_relevant_memories_cached(user, user_message, limit=5)
        except Exception as e:
            logger.warning(f"Failed to retrieve memories: {e}")
    
    # Get system prompt (with caching for base parts)
    system_prompt = get_system_prompt(user, relevant_memories)
    messages = [{"role": "system", "content": system_prompt}]
    
    # Limit history to last N messages to keep context manageable
    if len(history) > max_history:
        logger.debug(f"Truncating history from {len(history)} to {max_history} messages")
        history = history[-max_history:]
    
    # Add history (already formatted)
    for msg in history:
        if msg.get("role") in ["user", "assistant"]:
            messages.append({
                "role": msg["role"],
                "content": msg.get("content", "")
            })
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    return messages


def parse_action(response_text: str) -> Optional[Dict]:
    """
    Parse ACTION JSON from the LLM response if present.
    Supports both "ACTION:" (English) and "Ação:" (Portuguese).
    Also handles double braces {{ }} which LLM sometimes generates.
    Now also handles multi-line ACTION JSON.
    
    Args:
        response_text: Full LLM response
    
    Returns:
        Parsed action dict or None
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try to find ACTION: in the full text (not just per line)
    text_upper = response_text.upper()
    
    if 'ACTION:' in text_upper:
        try:
            # Find the position of ACTION:
            action_start = text_upper.index('ACTION:')
            # Extract everything after ACTION:
            action_part = response_text[action_start + 7:].strip()
            logger.debug(f"Found ACTION, extracted part length: {len(action_part)}, starts with: {action_part[:50]}")
            
            # Fix double braces ONLY at the very start (not throughout, as }} can be valid JSON)
            # Only replace {{ at position 0 and }} at the very end if they appear to be errors
            if action_part.startswith('{{'):
                action_part = '{' + action_part[2:]
                logger.debug("Fixed opening double brace")
            
            # Try to find the JSON object (starts with { and ends with })
            if action_part.startswith('{'):
                logger.debug(f"ACTION part starts with {{, full content ({len(action_part)} chars): {action_part}")
                # Count braces to find the complete JSON
                brace_count = 0
                json_end = 0
                in_string = False
                escape_next = False
                
                for i, char in enumerate(action_part):
                    # Handle string literals (ignore braces inside strings)
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"':
                        in_string = not in_string
                        continue
                    
                    # Only count braces outside of strings
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                
                logger.debug(f"Brace counting complete, json_end: {json_end}, final brace_count: {brace_count}")
                if json_end > 0:
                    action_json = action_part[:json_end]
                    # First attempt: raw parse
                    try:
                        logger.debug(f"Attempting to parse JSON: {action_json[:100]}")
                        parsed = json.loads(action_json)
                        logger.info(f"✓ Successfully parsed ACTION: {parsed}")
                        return parsed
                    except json.JSONDecodeError as e:
                        # Second attempt: normalize common LLM brace glitches ({{ }})
                        normalized = _normalize_llm_action_json(action_json)
                        logger.warning(
                            f"Failed to parse ACTION JSON on first attempt: {e}. "
                            f"Retrying with normalized braces."
                        )
                        parsed = json.loads(normalized)
                        logger.info(f"✓ Successfully parsed ACTION after normalization: {parsed}")
                        return parsed
                else:
                    logger.warning("json_end was 0, braces didn't balance")
            else:
                logger.warning(f"ACTION part doesn't start with {{, starts with: {action_part[:20]}")
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse ACTION JSON: {e}, raw: {action_part[:200] if 'action_part' in locals() else 'N/A'}")
        except Exception as e:
            logger.error(f"Unexpected error in parse_action: {e}", exc_info=True)
    
    elif 'AÇÃO:' in text_upper or 'ACAO:' in text_upper:
        try:
            # Find the position of Ação:
            if 'AÇÃO:' in text_upper:
                action_start = text_upper.index('AÇÃO:')
                offset = 5
            else:
                action_start = text_upper.index('ACAO:')
                offset = 5
            
            action_part = response_text[action_start + offset:].strip()
            
            # Fix double braces ONLY at the very start
            if action_part.startswith('{{'):
                action_part = '{' + action_part[2:]
            
            if action_part.startswith('{'):
                brace_count = 0
                json_end = 0
                for i, char in enumerate(action_part):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > 0:
                    action_json = action_part[:json_end]
                    try:
                        parsed = json.loads(action_json)
                        logger.debug(f"Successfully parsed AÇÃO: {parsed}")
                        return parsed
                    except json.JSONDecodeError:
                        normalized = _normalize_llm_action_json(action_json)
                        parsed = json.loads(normalized)
                        logger.debug(f"Successfully parsed AÇÃO after normalization: {parsed}")
                        return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse AÇÃO JSON: {e}")
    
    return None


def strip_action_line(response_text: str) -> str:
    """
    Remove a linha ACTION: {...} do texto de resposta do LLM.
    Remove também linhas que começam com "Ação:" (português).
    """
    lines = response_text.strip().split("\n")
    filtered = []
    for line in lines:
        stripped = line.strip()
        # Remove linhas que começam com ACTION: ou Ação: (case insensitive)
        if not (stripped.upper().startswith("ACTION:") or stripped.upper().startswith("AÇÃO:")):
            filtered.append(line)
    result = "\n".join(filtered).strip()
    # Also remove any trailing ACTION: or Ação: that might be in the same line
    if "ACTION:" in result.upper() or "AÇÃO:" in result.upper():
        # Find and remove ACTION: or Ação: and everything after it in the same line
        import re
        result = re.sub(r'\s*(ACTION|AÇÃO):.*$', '', result, flags=re.IGNORECASE | re.MULTILINE)
    return result.strip()


def handle_user_message(
    user: Optional[User],
    history: List[Dict],
    user_message: str,
    model: Optional[str] = None,
) -> Dict:
    """
    Orquestra a mensagem do utilizador:
    1) Constrói mensagens com build_messages
    2) Faz a 1ª chamada ao LLM
    3) Verifica se há ACTION
    4) Se ACTION == web_search:
       - faz pesquisa no backend
       - faz 2ª chamada ao LLM com resultados
       - devolve resposta final limpa
    5) Para outras ACTIONS, devolve resposta limpa + action dict
    
    Returns:
        Dict com:
        - reply: str - Resposta final limpa (sem linha ACTION)
        - action: Optional[Dict] - Action dict se houver (None se for web_search que já foi tratada)
        - used_search: bool - Se foi usada pesquisa web
        - search_results: Optional[List[Dict]] - Resultados da pesquisa se aplicável
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        base_messages = build_messages(history, user_message, user=user)
        logger.info(f"Built messages for Ollama, total messages: {len(base_messages)}")
        raw_response = call_ollama(base_messages, model=model)
        logger.info(f"Received raw response from Ollama, length: {len(raw_response)}")
    except Exception as e:
        logger.error(f"Error in handle_user_message during Ollama call: {str(e)}", exc_info=True)
        raise
    
    action = parse_action(raw_response)
    clean_response = strip_action_line(raw_response)
    
    # Debug logging
    logger.debug(f"Raw response: {raw_response[:200]}")
    logger.debug(f"Parsed action: {action}")
    logger.debug(f"Clean response: '{clean_response}'")
    logger.debug(f"Clean response stripped empty: {not clean_response.strip()}")
    
    # If response is empty after removing ACTION, provide default message
    # Handle both cases: when action is detected AND when response is empty but looks like it had ACTION
    if not clean_response.strip() and (action or 'ACTION:' in raw_response or 'save_note' in raw_response):
        # Try to parse action manually if parse_action failed
        if not action:
            logger.warning(f"parse_action() returned None but response seems to contain ACTION: {raw_response[:100]}")
            # Try manual parsing with double brace fix
            try:
                # Extract JSON from ACTION: line
                if 'ACTION:' in raw_response:
                    action_part = raw_response.split('ACTION:')[1].strip()
                    # Fix double braces
                    action_part = action_part.replace('{{', '{').replace('}}', '}')
                    action = json.loads(action_part)
                    logger.info(f"Manually parsed action with brace fix: {action}")
            except Exception as e:
                logger.error(f"Manual parsing also failed: {e}")
                # Fallback: at least detect the tool
                if 'save_note' in raw_response:
                    action = {'tool': 'save_note', 'args': {}}
                    logger.info("Manually detected save_note action (no args)")
        
        tool_name = action.get('tool', '') if action else ''
        if tool_name == 'save_note' or 'save_note' in raw_response:
            clean_response = "Vou criar essa nota para ti."
        elif tool_name == 'add_shopping_item' or 'add_shopping_item' in raw_response:
            clean_response = "Vou adicionar isso à lista de compras."
        elif tool_name == 'add_agenda_event' or 'add_agenda_event' in raw_response:
            clean_response = "Vou adicionar esse evento à agenda."
        elif tool_name == 'terminal_command' or 'terminal_command' in raw_response:
            clean_response = "Vou executar esse comando."
        elif tool_name == 'homeassistant_call_service' or 'homeassistant_call_service' in raw_response:
            clean_response = "Entendido, vou fazer isso."
        elif tool_name == 'homeassistant_get_states' or 'homeassistant_get_states' in raw_response:
            clean_response = "Vou verificar o estado dos dispositivos."
        else:
            clean_response = "Vou tratar disso."
        logger.info(f"Response was empty after ACTION removal, using default: {clean_response}")
    
    if not action:
        return {
            "reply": clean_response,
            "action": None,
            "used_search": False,
            "search_results": None,
        }
    
    # Se a ACTION for web_search, faz 2ª chamada com resultados
    if action.get("tool") == "web_search":
        query = action.get("args", {}).get("query", "")
        
        # Faz pesquisa web
        results = search_web(query)
        
        # Pega o system prompt da primeira chamada
        system_prompt = base_messages[0]["content"]
        
        # Constrói mensagens para a 2ª chamada:
        # - system prompt (mantém)
        # - histórico anterior
        # - resposta anterior do assistente (sem linha ACTION)
        # - nova mensagem user com resultados da pesquisa
        second_messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            *[m for m in base_messages[1:] if m["role"] in ("user", "assistant")],
            {"role": "assistant", "content": clean_response},
            {
                "role": "user",
                "content": (
                    "Aqui estão os resultados da pesquisa que encontraste. "
                    "Usa APENAS estes dados para responder de forma correta e sem contradições.\n\n"
                    f"{json.dumps(results, ensure_ascii=False, indent=2)}"
                ),
            },
        ]
        
        final_raw = call_ollama(second_messages, model=model)
        final_clean = strip_action_line(final_raw)
        
        return {
            "reply": final_clean,
            "action": None,
            "used_search": True,
            "search_results": results,
        }
    
    # Outras tools (agenda, notas, terminal, etc.) são tratadas noutro serviço
    return {
        "reply": clean_response,
        "action": action,
        "used_search": False,
        "search_results": None,
    }
