# SearXNG – Documentação da API Interna

## 1. Visão geral

O **SearXNG** é um meta-motor de pesquisa self-hosted que agrega resultados de vários motores de busca (DuckDuckGo, Wikipedia, etc.) sem expores diretamente o teu backend a esses serviços.

Nesta instância, tens:

- **Base URL da instância:** `http://192.168.1.73:8080`
- **Endpoint principal de pesquisa:** `GET /search`

Quando usas o parâmetro `format=json`, a API devolve os resultados em **JSON**, prontos a consumir no teu backend Django.

---

## 2. Configuração do container (Docker)

Trecho relevante do `docker-compose.yml` com as variáveis atuais:

```yaml
services:
  searxng:
    image: searxng/searxng:latest
    restart: unless-stopped
    depends_on:
      - redis
    ports:
      - "8080:8080"  # acedes em http://IP_DO_SERVIDOR:8080
    environment:
      - BASE_URL=http://192.168.1.73:8080/        # ajusta se tiveres domain / reverse proxy
      - INSTANCE_NAME=Personal Assistant Search
      - SEARXNG_SECRET=ajkngfajfdnasofnaseqweqndsdji1234123nsad
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./searxng:/etc/searxng

Com esta configuração:
	•	A instância fica acessível em http://192.168.1.73:8080.
	•	O SearXNG usa Redis como backend de cache/queue.
	•	As definições da instância (incluindo settings.yml) são lidas a partir de ./searxng no host.

⸻

3. Endpoint principal da API

GET /search

Consulta a web usando os motores configurados no settings.yml.

Parâmetros principais (query string)

Parâmetro	Obrigatório	Descrição	Exemplo
q	✔	Texto da pesquisa.	q=o que aconteceu no 25 de novembro em Portugal
format	✖	Formato da resposta. Para API, usar json.	format=json
language	✖	Idioma preferido (ex.: pt-PT, en).	language=pt-PT
safesearch	✖	Nível de safe search (0, 1, 2).	safesearch=1
engines	✖	Lista de motores específicos, separados por vírgulas. Se vazio, usa os defaults do settings.yml.	engines=duckduckgo,wikipedia
time_range	✖	Intervalo de tempo (day, week, month, year).	time_range=week
categories	✖	Categorias de pesquisa (general, news, images, it, etc.).	categories=news
page	✖	Número da página (para paginação).	page=2

Exemplo de URL

http://192.168.1.73:8080/search?q=o+que+aconteceu+no+25+de+novembro+em+Portugal&format=json&language=pt-PT&safesearch=1


⸻

4. Exemplo de resposta JSON

Estrutura típica (simplificada):

{
  "query": "o que aconteceu no 25 de novembro em Portugal",
  "number_of_results": 12345,
  "results": [
    {
      "title": "25 de Novembro de 1975 – o que foi?",
      "url": "https://exemplo.com/artigo-25-novembro",
      "content": "Texto de resumo / snippet do resultado...",
      "engine": "duckduckgo",
      "category": "general"
    },
    {
      "title": "História do 25 de Novembro em Portugal",
      "url": "https://outrosite.pt/25-novembro",
      "content": "Outro resumo...",
      "engine": "wikipedia",
      "category": "general"
    }
  ]
}

Campos importantes em results[]:
	•	title – título da página.
	•	url – link final do resultado.
	•	content – snippet / resumo textual.
	•	engine – motor que devolveu o resultado (ex.: duckduckgo, wikipedia).
	•	category – categoria do resultado (general, news, images, etc.).

⸻

5. Exemplos de utilização da API

5.1. curl

curl "http://192.168.1.73:8080/search?q=o+que+aconteceu+no+25+de+novembro+em+Portugal&format=json&language=pt-PT&safesearch=1"


⸻

5.2. Python (requests) – função genérica

import requests

SEARXNG_BASE_URL = "http://192.168.1.73:8080"

def searxng_search(query: str, num_results: int = 5):
    params = {
        "q": query,
        "format": "json",
        "language": "pt-PT",
        "safesearch": 1,
    }

    resp = requests.get(f"{SEARXNG_BASE_URL}/search", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("results", [])[:num_results]:
        results.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "snippet": item.get("content"),
            "engine": item.get("engine"),
        })
    return results


⸻

6. Integração com Django (web_search_service)

6.1. Serviço de pesquisa

assistant/services/web_search_service.py:

import logging
import requests

logger = logging.getLogger(__name__)

SEARXNG_BASE_URL = "http://192.168.1.73:8080"

class WebSearchError(Exception):
    pass

def search_web_with_searxng(user_id: int, query: str, limit: int = 5):
    logger.info("Web search requested for user %s, query: %s", user_id, query)

    params = {
        "q": query,
        "format": "json",
        "language": "pt-PT",
        "safesearch": 1,
    }

    try:
        resp = requests.get(
            f"{SEARXNG_BASE_URL}/search",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception("SearXNG request failed: %s", e)
        raise WebSearchError("Erro ao consultar SearXNG") from e

    data = resp.json()
    raw_results = data.get("results", [])[:limit]

    results = [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content"),
            "engine": r.get("engine"),
        }
        for r in raw_results
    ]

    logger.info("Web search returned %d results via SearXNG", len(results))
    return results

6.2. Uso numa view (exemplo simplificado)

# assistant/views.py
from .services.web_search_service import search_web_with_searxng

def handle_chat_request(request):
    # Exemplo simplificado – adapta ao teu código real
    payload = request.data
    user = request.user
    query = payload["query"]

    results = search_web_with_searxng(user.id, query)

    # Aqui podes:
    # - formatar `results` para JSON de resposta da API
    # - ou passar os resultados para o teu LLM / lógica de assistente


⸻

7. Parâmetros extra úteis
	•	Filtrar por categoria de notícias:

&categories=news


	•	Resultados recentes (última semana / mês):

&time_range=week
# ou
&time_range=month


	•	Usar motores específicos:

&engines=duckduckgo,wikipedia


	•	Paginação:

&page=2



⸻

8. Boas práticas
	•	Define sempre um timeout nas chamadas HTTP (por ex.: timeout=10) para evitar bloquear o backend.
	•	Limita o número de resultados (ex.: [:5] ou [:10]) e resume apenas o essencial (título, URL, snippet, engine).
	•	Usa logging informativo (como nos exemplos) para poderes diagnosticar problemas rapidamente.
	•	Se no futuro mudares o IP/porta ou colocares a instância atrás de Traefik com HTTPS, basta atualizar:
	•	BASE_URL no docker-compose.yml do SearXNG;
	•	SEARXNG_BASE_URL no teu código Django.

⸻


