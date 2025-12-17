"""
Service for performing web searches.
Uses SearXNG self-hosted search engine which aggregates results from multiple sources.
"""
from typing import List, Dict, Optional
import logging
import time
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# --- Simple in-memory cache (por processo) ---
_SEARCH_CACHE: dict = {}
CACHE_TTL_SECONDS = 60 * 5  # 5 minutos


# Session global para reutilizar ligações HTTP
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Jarvas/1.0 (+internal-personal-assistant)",
    "Accept": "application/json",
    # Estes 2 ajudam a calar o aviso do SearXNG:
    "X-Forwarded-For": "192.168.1.73",  # ou o IP do cliente se um dia quiseres
    "X-Real-IP": "192.168.1.73",
})


def _get_from_cache(query: str, max_results: int) -> List[Dict[str, str]] | None:
    key = (query, max_results)
    entry = _SEARCH_CACHE.get(key)
    if not entry:
        return None

    ts, results = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        # expirado
        _SEARCH_CACHE.pop(key, None)
        return None

    logger.info(f"Using cached search results for query='{query}'")
    return results


def _set_cache(query: str, max_results: int, results: List[Dict[str, str]]) -> None:
    key = (query, max_results)
    _SEARCH_CACHE[key] = (time.time(), results)


def search_web(query: str, max_results: int = 5, retries: int = 3) -> List[Dict[str, str]]:
    """
    Perform a web search using SearXNG and return results.
    Includes retry logic with exponential backoff to handle errors.
    """
    searxng_url = getattr(settings, 'SEARXNG_BASE_URL', 'http://192.168.1.73:8080')

    # 1) Ver cache primeiro
    cached = _get_from_cache(query, max_results)
    if cached is not None:
        return cached

    for attempt in range(retries):
        try:
            logger.info(f"Starting SearXNG search for: {query} (attempt {attempt + 1}/{retries})")

            params = {
                "q": query,
                "format": "json",
                "language": "pt-PT",
                "safesearch": 1,
                # Opcional: se quiseres limitar engines mesmo que no settings.yml tenhas mais:
                # "engines": "duckduckgo,wikipedia",
            }

            response = SESSION.get(
                f"{searxng_url}/search",
                params=params,
                timeout=10,
            )

            # Se for rate-limit do SearXNG ou algum engine, tende a vir como 429
            if response.status_code == 429:
                logger.warning(
                    f"SearXNG returned 429 Too Many Requests for query='{query}'. "
                    f"Attempt {attempt + 1}/{retries}"
                )
                # Aqui não vale a pena martelar mais → sai logo para fallback na última tentativa
                if attempt == retries - 1:
                    return search_web_fallback(query, max_results)
                time.sleep(2 ** attempt)
                continue

            response.raise_for_status()

            # Check if response is empty
            if not response.text or len(response.text.strip()) == 0:
                logger.warning(
                    f"SearXNG returned empty response on attempt {attempt + 1}/{retries}. "
                    f"Status: {response.status_code}"
                )
                if attempt == retries - 1:
                    logger.error("All retries exhausted, trying fallback method")
                    return search_web_fallback(query, max_results)
                time.sleep(2 ** attempt)
                continue

            # Check content type before parsing JSON
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' not in content_type:
                logger.warning(
                    f"SearXNG returned non-JSON content type: {content_type}. "
                    f"Response preview: {response.text[:200]}"
                )
                if attempt == retries - 1:
                    logger.error("All retries exhausted, trying fallback method")
                    return search_web_fallback(query, max_results)
                time.sleep(2 ** attempt)
                continue

            try:
                data = response.json()
            except (ValueError, requests.exceptions.JSONDecodeError) as e:
                logger.error(
                    f"Failed to parse JSON response from SearXNG: {e}. "
                    f"Response status: {response.status_code}, "
                    f"Content-Type: {content_type}, "
                    f"Response length: {len(response.text)}, "
                    f"Response preview: {response.text[:500]}"
                )
                if attempt == retries - 1:
                    logger.error("All retries exhausted, trying fallback method")
                    return search_web_fallback(query, max_results)
                time.sleep(2 ** attempt)
                continue

            logger.debug(f"SearXNG response keys: {list(data.keys())}")
            logger.debug(f"SearXNG response has 'results': {'results' in data}")
            
            raw_results = data.get("results", [])
            logger.info(f"SearXNG returned {len(raw_results)} raw results")
            
            if not raw_results:
                logger.warning(f"SearXNG returned empty results list for query: {query}")
                logger.debug(f"Full response data: {data}")
            
            raw_results = raw_results[:max_results]

            results: List[Dict[str, str]] = []
            for item in raw_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "engine": item.get("engine", ""),
                })

            logger.info(f"SearXNG search completed, found {len(results)} results")

            # guardar em cache
            _set_cache(query, max_results, results)

            return results

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}/{retries}")
            if attempt == retries - 1:
                logger.error("All retries exhausted due to timeout")
                return []
            time.sleep(2 ** attempt)
            continue

        except requests.exceptions.RequestException as e:
            # Se tiver response, podemos inspecionar código HTTP
            status = getattr(getattr(e, "response", None), "status_code", None)
            
            # Check if it's a JSON decode error (response might be empty or HTML)
            if isinstance(e, requests.exceptions.JSONDecodeError) or "JSON" in str(type(e)):
                response_obj = getattr(e, "response", None)
                if response_obj:
                    content_type = response_obj.headers.get('content-type', '').lower()
                    logger.error(
                        f"JSON decode error on attempt {attempt + 1}/{retries}. "
                        f"Status: {status}, Content-Type: {content_type}, "
                        f"Response preview: {response_obj.text[:500] if hasattr(response_obj, 'text') else 'N/A'}"
                    )
                else:
                    logger.error(f"JSON decode error on attempt {attempt + 1}/{retries}: {e}")
            else:
                logger.warning(
                    f"Request error on attempt {attempt + 1}/{retries} "
                    f"(status={status}): {e}"
                )
            
            if attempt == retries - 1:
                logger.error("All retries exhausted, trying fallback method")
                return search_web_fallback(query, max_results)
            time.sleep(2 ** attempt)
            continue

        except Exception as e:
            logger.error(f"Unexpected error performing web search: {e}", exc_info=True)
            if attempt == retries - 1:
                logger.error("All retries exhausted, trying fallback method")
                return search_web_fallback(query, max_results)
            time.sleep(2 ** attempt)
            continue

    return []

def search_web_fallback(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Fallback search method using DuckDuckGo directly.
    This is used when SearXNG is unavailable.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
    
    Returns:
        List of dictionaries with 'title', 'url', and 'snippet' keys
    """
    try:
        from duckduckgo_search import DDGS
        
        logger.info(f"Trying DuckDuckGo fallback search for: {query}")
        
        with DDGS() as ddgs:
            results = []
            search_iter = ddgs.text(query, max_results=max_results)
            for result in search_iter:
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('body', ''),
                    'engine': 'duckduckgo',
                })
            
            if results:
                logger.info(f"Fallback search found {len(results)} results")
            else:
                logger.warning("Fallback search found no results")
            
            return results
            
    except ImportError:
        logger.warning("duckduckgo-search not installed, cannot use fallback method")
        return []
    except Exception as e:
        logger.error(f"Error in fallback search method: {e}", exc_info=True)
        return []


def format_search_results(results: List[Dict[str, str]]) -> str:
    """
    Format search results into a readable string for the LLM.
    
    Args:
        results: List of search result dictionaries
    
    Returns:
        Formatted string with search results
    """
    if not results:
        return "Nenhum resultado encontrado."
    
    formatted = "Resultados da pesquisa:\n\n"
    for i, result in enumerate(results, 1):
        engine = result.get('engine', '')
        engine_info = f" (fonte: {engine})" if engine else ""
        formatted += f"{i}. {result.get('title', 'Sem título')}{engine_info}\n"
        formatted += f"   URL: {result.get('url', '')}\n"
        formatted += f"   {result.get('snippet', 'Sem descrição')}\n\n"
    
    return formatted

