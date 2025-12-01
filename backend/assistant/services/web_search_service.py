"""
Service for performing web searches.
Uses SearXNG self-hosted search engine which aggregates results from multiple sources.
"""
from typing import List, Dict, Optional
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5, retries: int = 3) -> List[Dict[str, str]]:
    """
    Perform a web search using SearXNG and return results.
    Includes retry logic with exponential backoff to handle errors.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        retries: Number of retry attempts if request fails
    
    Returns:
        List of dictionaries with 'title', 'url', and 'snippet' keys
    """
    searxng_url = getattr(settings, 'SEARXNG_BASE_URL', 'http://192.168.1.73:8080')
    
    for attempt in range(retries):
        try:
            logger.info(f"Starting SearXNG search for: {query} (attempt {attempt + 1}/{retries})")
            
            params = {
                'q': query,
                'format': 'json',
                'language': 'pt-PT',
                'safesearch': 1,
            }
            
            response = requests.get(
                f"{searxng_url}/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            raw_results = data.get('results', [])[:max_results]
            
            results = []
            for item in raw_results:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('content', ''),
                    'engine': item.get('engine', ''),
                })
            
            logger.info(f"SearXNG search completed, found {len(results)} results")
            return results
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}/{retries}")
            if attempt == retries - 1:
                logger.error("All retries exhausted due to timeout")
                return []
            continue
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error on attempt {attempt + 1}/{retries}: {e}")
            if attempt == retries - 1:
                logger.error("All retries exhausted, trying fallback method")
                return search_web_fallback(query, max_results)
            # Wait before retry (exponential backoff)
            import time
            time.sleep(2 ** attempt)
            continue
            
        except Exception as e:
            logger.error(f"Unexpected error performing web search: {e}", exc_info=True)
            if attempt == retries - 1:
                logger.error("All retries exhausted, trying fallback method")
                return search_web_fallback(query, max_results)
            import time
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

