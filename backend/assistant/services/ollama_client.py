import json
import requests
from typing import List, Dict, Optional
from django.conf import settings
from datetime import datetime, timezone
from django.contrib.auth.models import User
from .memory_service import search_memories, extract_memories_from_conversation
from .web_search_service import search_web
from ..models import DeviceAlias, HomeAssistantConfig
from .homeassistant_client import get_homeassistant_states

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
        
        # Get states to find climate devices
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
    """Get system prompt with current date/time information."""
    now = datetime.now(timezone.utc)
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    current_datetime_iso = now.isoformat()
    current_month = now.month

    # Determine season (Northern Hemisphere)
    # Winter: Dec (12), Jan (1), Feb (2)
    # Summer: Jun (6), Jul (7), Aug (8)
    is_winter = current_month in [12, 1, 2]
    is_summer = current_month in [6, 7, 8]
    season = "inverno" if is_winter else "verão" if is_summer else "outono/primavera"
    default_hvac_mode = "heat" if is_winter else ("cool" if is_summer else "auto")

    memories_section = ""
    if relevant_memories:
        memories_section = "\n\nRELEVANT MEMORIES (coisas que sabes sobre o utilizador):\n"
        for i, memory in enumerate(relevant_memories, 1):
            memories_section += f"{i}. {memory.get('content', '')}\n"
        memories_section += "\nUsa estas memórias para dar respostas mais personalizadas e com contexto. Faz referência a elas de forma natural quando fizer sentido.\n"
    
    ha_devices_section = get_homeassistant_devices_info(user)
    
    # Build example with proper escaping
    example_action = f'{{"tool": "homeassistant_call_service", "args": {{"domain": "climate", "service": "set_temperature", "data": {{"entity_id": "climate.cozinha", "temperature": 25, "hvac_mode": "{default_hvac_mode}"}}}}}}'

    return f"""Tu és o Jarvas, assistente pessoal do utilizador Marco.
És um assistente conversacional em português de Portugal, simpático, direto e útil.
Ajudas com:
- Listas de compras detalhadas (itens, quantidades, lojas, notas)
- Agenda e eventos
- Notas e memória pessoal
- Controlo da casa inteligente via Home Assistant (ar condicionados, luzes, etc.)
- Perguntas gerais sobre tecnologia, desporto, atualidade, etc.

INFORMAÇÃO TEMPORAL (MUITO IMPORTANTE):
- Data atual (UTC): {current_date}
- Hora atual (UTC): {current_time}
- Datetime atual ISO: {current_datetime_iso}

Quando o utilizador disser "hoje", "amanhã", "para a semana", etc.:
- "hoje" = {current_date}
- "amanhã" = dia seguinte a {current_date}
Sempre que tiveres de escrever datas em JSON de ações, usa o formato ISO 8601 (YYYY-MM-DDTHH:MM:SS+00:00).

{memories_section}
{ha_devices_section}
REGRAS GERAIS DE RESPOSTA:
- Responde SEMPRE em português de Portugal.
- Explica as coisas com clareza, mas sem ser demasiado formal.
- Se não tiveres a certeza de algo, diz que não tens a certeza em vez de inventar.
- Se a pergunta envolver factos que mudam no tempo (resultados, classificações, preços, horários, notícias, etc.), assume por defeito que deves usar web_search.

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
  
  CONTROLO DE AR CONDICIONADOS (MUITO IMPORTANTE):
  - Estamos atualmente em {season} (mês {current_month}).
  - Se for INVERNO (Dez, Jan, Fev): usa hvac_mode: "heat" para aquecer.
  - Se for VERÃO (Jun, Jul, Ago): usa hvac_mode: "cool" para arrefecer.
  - Se for outono/primavera: pergunta ao utilizador se quer "heat" ou "cool", ou usa "auto".
  
  AR CONDICIONADOS DISPONÍVEIS:
{ha_devices_section}
  
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
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error calling Ollama: {str(e)}")


def build_messages(history: List[Dict], user_message: str, user: Optional[User] = None) -> List[Dict[str, str]]:
    """
    Build the message list for Ollama, including system prompt with current date/time and relevant memories.
    
    Args:
        history: Previous conversation history
        user_message: Current user message
        user: Optional user instance for memory retrieval
    
    Returns:
        List of messages formatted for Ollama
    """
    # Search for relevant memories if user is provided
    relevant_memories = []
    if user:
        try:
            memories = search_memories(user, user_message, limit=5)
            relevant_memories = [
                {'content': mem.content, 'type': mem.memory_type}
                for mem in memories
            ]
        except Exception as e:
            # If memory search fails, continue without memories
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to retrieve memories: {e}")
    
    # Get system prompt with current date/time and memories (generated fresh each time)
    system_prompt = get_system_prompt(user, relevant_memories)
    messages = [{"role": "system", "content": system_prompt}]
    
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
    
    Args:
        response_text: Full LLM response
    
    Returns:
        Parsed action dict or None
    """
    lines = response_text.strip().split('\n')
    
    for line in reversed(lines):  # Check from the end
        line = line.strip()
        if line.startswith('ACTION:'):
            try:
                action_json = line.replace('ACTION:', '').strip()
                return json.loads(action_json)
            except (json.JSONDecodeError, ValueError):
                return None
    
    return None


def strip_action_line(response_text: str) -> str:
    """
    Remove a linha ACTION: {...} do texto de resposta do LLM.
    """
    lines = response_text.strip().split("\n")
    filtered = []
    for line in lines:
        stripped = line.strip()
        # Remove linhas que começam com ACTION: (case insensitive)
        if not stripped.upper().startswith("ACTION:"):
            filtered.append(line)
    result = "\n".join(filtered).strip()
    # Also remove any trailing ACTION: that might be in the same line
    if "ACTION:" in result.upper():
        # Find and remove ACTION: and everything after it in the same line
        import re
        result = re.sub(r'\s*ACTION:.*$', '', result, flags=re.IGNORECASE | re.MULTILINE)
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
    base_messages = build_messages(history, user_message, user=user)
    raw_response = call_ollama(base_messages, model=model)
    
    action = parse_action(raw_response)
    clean_response = strip_action_line(raw_response)
    
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

