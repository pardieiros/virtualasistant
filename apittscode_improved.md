# Improved STT API Code with Better Error Handling

## Key Improvements:

1. **Logging no início do worker** - para ver se o thread inicia
2. **Try/except mais abrangente** - captura erros antes do lock
3. **Logging de exceções** - para debug
4. **Verificação do thread** - confirma que o thread foi iniciado

## Código melhorado:

```python
import logging

# Adicionar no início do ficheiro
logger = logging.getLogger(__name__)

def _worker(job_id: str, filename: str, lang: str, model_name: str, diarize: bool):
    """Worker function with improved error handling."""
    logger.info(f"Worker thread started for job {job_id}, file: {filename}")
    
    try:
        with PROCESS_LOCK:
            logger.info(f"Worker {job_id} acquired lock, starting processing")
            try:
                _set_job(job_id, {"status": "processing", "started_at": time.time()})
                _log_event(job_id, f"Job started for file: {filename}", stage="start", progress=1)

                # Validar path (evita path traversal)
                src = (VIDEOS_DIR / filename).resolve()
                logger.info(f"Worker {job_id}: Checking file at {src}")
                
                if not str(src).startswith(str(VIDEOS_DIR)) or not src.exists():
                    error_msg = f"File not found: {src} (VIDEOS_DIR: {VIDEOS_DIR})"
                    logger.error(f"Worker {job_id}: {error_msg}")
                    _set_job(job_id, {"status": "error", "error": error_msg})
                    _log_event(job_id, "File not found.", stage="error")
                    return

                # ... resto do código ...
                
            except Exception as e:
                error_msg = f"Error in worker {job_id}: {str(e)}"
                logger.exception(f"Worker {job_id} failed: {e}")
                _set_job(job_id, {"status": "error", "error": str(e)})
                _log_event(job_id, f"Error: {e}", stage="error")
    except Exception as e:
        # Erro ao adquirir lock ou antes de entrar no lock
        logger.exception(f"Worker {job_id} failed before lock: {e}")
        _set_job(job_id, {"status": "error", "error": f"Worker failed to start: {str(e)}"})
        _log_event(job_id, f"Worker failed: {e}", stage="error")

@app.post("/jobs")
def create_job(req: CreateJobRequest):
    # ... código existente ...
    
    t = threading.Thread(target=_worker, args=(job_id, req.filename, req.lang, req.model, req.diarize), daemon=True)
    t.start()
    logger.info(f"Started worker thread for job {job_id}, thread alive: {t.is_alive()}")
    
    return {"job_id": job_id, "status": "queued"}
```

## Verificações a fazer:

1. **Verificar se o thread inicia**: Adicionar `logger.info` após `t.start()`
2. **Verificar se o worker entra no lock**: Adicionar logging dentro do `with PROCESS_LOCK:`
3. **Verificar se o ficheiro existe**: Log do caminho completo antes de verificar
4. **Verificar exceções**: Capturar todas as exceções e logar
