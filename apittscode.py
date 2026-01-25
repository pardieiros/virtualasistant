import os

# Disable XET for Hugging Face Hub (fixes network download issues)
# MUST be set BEFORE importing whisperx or any huggingface_hub modules
# Set multiple environment variables to ensure XET is disabled
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
# Force use of regular HTTP download instead of XET
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
# Disable XET completely - newer versions may use this
os.environ["HF_HUB_DISABLE_XET_CAS"] = "1"
# Use regular snapshot download instead of XET
os.environ["HF_HUB_USE_XET"] = "0"

import uuid
import json
import time
import shutil
import threading
import subprocess
import logging
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Fix PyTorch 2.6 weights_only issue with omegaconf and typing
# This must be done BEFORE importing whisperx or any models
# PyTorch 2.6+ changed default to weights_only=True for security, but this breaks
## ---- PyTorch 2.6+ weights_only fix (MUST run before importing whisperx/pyannote) ----
# ---- PyTorch 2.6+ weights_only fix (MUST run before importing whisperx/pyannote) ----
try:
    import torch
    import collections
    import pathlib
    import typing

    # ✅ PyTorch 2.6+ fix: force weights_only=False for pyannote checkpoints
    _orig_torch_load = torch.load
    def _torch_load_no_weights_only(*args, **kwargs):
        kwargs["weights_only"] = False
        return _orig_torch_load(*args, **kwargs)
    
    torch.load = _torch_load_no_weights_only

    safe = [
        # builtins comuns em checkpoints
        list, dict, tuple, set, frozenset,
        int, float, bool, str, bytes,
        type, None.__class__,

        # collections
        collections.defaultdict,
        collections.OrderedDict,

        # pathlib
        pathlib.PosixPath,
        pathlib.WindowsPath,

        # typing
        typing.Any,
    ]

    # TorchVersion (usado em checkpoints do PyTorch)
    try:
        from torch.torch_version import TorchVersion
        safe += [TorchVersion]
    except Exception:
        pass

    # OmegaConf (aparece MUITO em checkpoints do pyannote)
    try:
        import omegaconf
        from omegaconf import DictConfig, ListConfig
        from omegaconf.base import ContainerMetadata

        # nodes (o teu erro atual: AnyNode)
        from omegaconf.nodes import AnyNode, ValueNode

        safe += [
            DictConfig, ListConfig, ContainerMetadata,
            AnyNode, ValueNode,
        ]
    except Exception:
        pass

    # pyannote.audio Specifications (usado em checkpoints do pyannote)
    # Nota: Não importar pyannote aqui (melhor prática)
    try:
        from pyannote.audio.core.task import Specifications
        safe += [Specifications]
    except Exception:
        pass

    torch.serialization.add_safe_globals(safe)
except Exception:
    pass
# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
# Patch huggingface_hub to disable XET before importing whisperx
try:
    import huggingface_hub
    # Force disable XET at module level
    if hasattr(huggingface_hub, 'file_download'):
        # Monkey patch to disable XET by making it raise an error that will trigger fallback
        try:
            original_xet_get = huggingface_hub.file_download.xet_get
            def disabled_xet_get(*args, **kwargs):
                # Raise an error that will cause fallback to regular HTTP
                raise ConnectionError("XET is disabled - forcing HTTP fallback")
            huggingface_hub.file_download.xet_get = disabled_xet_get
        except AttributeError:
            pass  # xet_get might not exist in this version
except Exception as patch_error:
    pass  # If patching fails, continue anyway

import whisperx

# ---- DIARIZATION IMPORT (compatível com várias versões do whisperx) ----
DiarizationPipeline = None

try:
    # versões antigas
    from whisperx.diarize import DiarizationPipeline  # type: ignore
except Exception:
    try:
        # algumas versões expõem no root
        from whisperx import DiarizationPipeline  # type: ignore
    except Exception:
        DiarizationPipeline = None

# === CONFIG ===
VIDEOS_DIR = Path("/srv/smb/videos").resolve()                # pasta SMB montada
WORK_DIR = Path("/opt/transcribe/work").resolve()             # trabalho local (evita ler do SMB durante horas)
RESULTS_DIR = Path("/opt/transcribe/results").resolve()       # resultados
LOG_DIR = Path("/srv/smb/videos/inbox").resolve()            # pasta para logs
WORK_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# === LOGGING SETUP ===
LOG_FILE = LOG_DIR / f"transcribe_api_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN", "REDACTED_HF_TOKEN")  # para diarização pyannote

# GPU/CPU settings (ajusta)
DEVICE = os.getenv("ASR_DEVICE", "cpu")            # "cuda" para RTX, "cpu" para teste
COMPUTE_TYPE = os.getenv("ASR_COMPUTE", "int8")    # ex: "float16" (cuda), "int8" (cpu)

# Concurrency: 1 job de cada vez
PROCESS_LOCK = threading.Lock()

# Jobs em memória + persistência simples
JOBS_FILE = RESULTS_DIR / "jobs.json"
JOBS_LOCK = threading.Lock()

# SSE subscribers por job
JOB_EVENTS: Dict[str, list] = {}
JOB_EVENTS_LOCK = threading.Lock()


app = FastAPI(title="Transcribe + Diarize API")


# =========================
# Helpers: Jobs persistence
# =========================
def _load_jobs() -> Dict[str, Any]:
    if not JOBS_FILE.exists():
        return {}
    try:
        return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_jobs(jobs: Dict[str, Any]) -> None:
    JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def _set_job(job_id: str, patch: Dict[str, Any]) -> None:
    with JOBS_LOCK:
        jobs = _load_jobs()
        job = jobs.get(job_id, {})
        job.update(patch)
        jobs[job_id] = job
        _save_jobs(jobs)


def _get_job(job_id: str) -> Dict[str, Any]:
    with JOBS_LOCK:
        jobs = _load_jobs()
        if job_id not in jobs:
            raise KeyError(job_id)
        return jobs[job_id]


def _log_event(job_id: str, message: str, stage: Optional[str] = None, progress: Optional[int] = None):
    evt = {
        "ts": time.time(),
        "message": message,
        "stage": stage,
        "progress": progress,
    }
    # guardar em job.logs também
    job = _get_job(job_id)
    logs = job.get("logs", [])
    logs.append(evt)
    _set_job(job_id, {"logs": logs})
    # SSE push
    with JOB_EVENTS_LOCK:
        JOB_EVENTS.setdefault(job_id, []).append(evt)


# =========================
# Audio + formatting
# =========================
def extract_audio_to_wav(input_path: Path, wav_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def format_segments_with_speakers(segments):
    # map SPEAKER_00 -> User1 etc.
    speaker_map = {}
    user_idx = 1

    lines = []
    for seg in segments:
        spk = seg.get("speaker", "SPEAKER_??")
        if spk not in speaker_map:
            speaker_map[spk] = f"User{user_idx}"
            user_idx += 1

        txt = (seg.get("text") or "").strip()
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", 0.0))
        if txt:
            lines.append(f"[{start:07.2f}-{end:07.2f}] {speaker_map[spk]}: {txt}")

    return "\n".join(lines).strip()


# =========================
# Request models
# =========================
class CreateJobRequest(BaseModel):
    filename: str = Field(..., description="Nome do ficheiro dentro de /srv/smb/videos")
    lang: str = Field("pt", description="pt, en, auto")
    model: str = Field("small", description="tiny/base/small/medium/large-v2 etc (whisperx)")
    diarize: bool = Field(True, description="Se true, tenta diarização (HF_TOKEN necessário).")


# =========================
# Worker
# =========================
def _worker(job_id: str, filename: str, lang: str, model_name: str, diarize: bool):
    logger.info(f"Worker thread started for job {job_id}, file: {filename}")
    
    # Log device info
    try:
        if DEVICE == "cuda":
            import torch
            logger.info(f"Worker {job_id}: CUDA available: {torch.cuda.is_available()}, device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}")
            if torch.cuda.is_available():
                logger.info(f"Worker {job_id}: CUDA device name: {torch.cuda.get_device_name(0)}, memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
    except Exception as device_check_error:
        logger.warning(f"Worker {job_id}: Could not check CUDA status: {device_check_error}")
    
    try:
        with PROCESS_LOCK:
            logger.info(f"Worker {job_id} acquired PROCESS_LOCK, starting processing")
            try:
                _set_job(job_id, {"status": "processing", "started_at": time.time()})
                _log_event(job_id, f"Job started for file: {filename}", stage="start", progress=1)
                logger.info(f"Worker {job_id}: Status changed to processing")

                # Validar path (evita path traversal)
                src = (VIDEOS_DIR / filename).resolve()
                logger.info(f"Worker {job_id}: Checking file at {src} (VIDEOS_DIR: {VIDEOS_DIR})")
                
                if not str(src).startswith(str(VIDEOS_DIR)) or not src.exists():
                    error_msg = f"File not found: {src} (VIDEOS_DIR: {VIDEOS_DIR})"
                    logger.error(f"Worker {job_id}: {error_msg}")
                    _set_job(job_id, {"status": "error", "error": error_msg})
                    _log_event(job_id, "File not found.", stage="error")
                    return
                
                logger.info(f"Worker {job_id}: File found, size: {src.stat().st_size} bytes")

                # Criar work dir
                job_work = (WORK_DIR / job_id).resolve()
                job_work.mkdir(parents=True, exist_ok=True)
                logger.info(f"Worker {job_id}: Created work directory: {job_work}")

                # Copiar para local (muito importante para estabilidade/performance)
                _log_event(job_id, "Copying video locally...", stage="copy", progress=5)
                logger.info(f"Worker {job_id}: Copying video from {src} to {job_work}")
                local_video = job_work / src.name
                shutil.copy2(src, local_video)
                logger.info(f"Worker {job_id}: Video copied successfully")

                # Extrair áudio
                wav_path = job_work / "audio.wav"
                _log_event(job_id, "Extracting audio (ffmpeg)...", stage="extract_audio", progress=15)
                logger.info(f"Worker {job_id}: Extracting audio with ffmpeg")
                extract_audio_to_wav(local_video, wav_path)
                logger.info(f"Worker {job_id}: Audio extraction completed")

                # ASR
                _log_event(job_id, f"Loading ASR model: {model_name} (device={DEVICE}, compute={COMPUTE_TYPE})",
                          stage="load_asr", progress=25)
                logger.info(f"Worker {job_id}: Loading ASR model: {model_name} (device={DEVICE}, compute={COMPUTE_TYPE})")
                
                # Check Hugging Face cache
                try:
                    from huggingface_hub import snapshot_download
                    cache_dir = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
                    logger.info(f"Worker {job_id}: Hugging Face cache directory: {cache_dir}")
                except Exception as cache_check_error:
                    logger.warning(f"Worker {job_id}: Could not check HF cache: {cache_check_error}")
                
                logger.info(f"Worker {job_id}: About to call whisperx.load_model() - this may take a while (downloading from Hugging Face if not cached)...")
                logger.info(f"Worker {job_id}: NOTE: Model '{model_name}' is large (~3GB for large-v2). Download may take 5-15 minutes depending on internet speed.")
                # Verify XET is disabled
                hf_disable_xet = os.environ.get('HF_HUB_DISABLE_XET', 'not set')
                logger.info(f"Worker {job_id}: XET disabled via HF_HUB_DISABLE_XET={hf_disable_xet}")
                if hf_disable_xet != "1":
                    logger.warning(f"Worker {job_id}: WARNING: HF_HUB_DISABLE_XET is not set to '1'! Setting it now...")
                    os.environ["HF_HUB_DISABLE_XET"] = "1"
                
                # Try to disable XET programmatically as well
                try:
                    import huggingface_hub
                    # Force disable XET if possible
                    if hasattr(huggingface_hub, 'constants'):
                        huggingface_hub.constants.HF_HUB_DISABLE_XET = True
                    logger.info(f"Worker {job_id}: Attempted to disable XET programmatically")
                except Exception as xet_disable_error:
                    logger.warning(f"Worker {job_id}: Could not disable XET programmatically: {xet_disable_error}")
                
                # Check if model is in cache first
                cache_dir = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
                model_in_cache = False
                try:
                    from faster_whisper import WhisperModel
                    # Try to load with local_files_only to check cache
                    try:
                        test_model = WhisperModel(model_name, device="cpu", local_files_only=True)
                        model_in_cache = True
                        logger.info(f"Worker {job_id}: Model '{model_name}' found in cache!")
                        del test_model  # Clean up
                    except Exception:
                        logger.info(f"Worker {job_id}: Model '{model_name}' not in cache, will attempt download")
                except Exception as cache_check_error:
                    logger.warning(f"Worker {job_id}: Could not check cache: {cache_check_error}")
                
                load_start_time = time.time()
                
                # Start a thread to log progress periodically
                load_complete = threading.Event()
                def log_progress():
                    elapsed = 0
                    while not load_complete.is_set():
                        time.sleep(30)  # Log every 30 seconds
                        if not load_complete.is_set():
                            elapsed = time.time() - load_start_time
                            logger.info(f"Worker {job_id}: Still loading model '{model_name}'... ({elapsed:.0f} seconds elapsed)")
                            _log_event(job_id, f"Loading model... ({elapsed:.0f}s)", stage="load_asr", progress=25)
                
                progress_thread = threading.Thread(target=log_progress, daemon=True)
                progress_thread.start()
                
                # helper: sempre usar silero para VAD (evita pyannote no load_model)
                def load_asr(model_name: str, local_only: bool):
                    return whisperx.load_model(
                        model_name,
                        DEVICE,
                        compute_type=COMPUTE_TYPE,
                        vad_method="silero",              # <<< FIX PRINCIPAL
                        vad_options={"min_silence_duration_ms": 500},
                        local_files_only=local_only
                    )
                
                try:
                    if model_in_cache:
                        logger.info(f"Worker {job_id}: Loading model from cache (local_files_only=True) ...")
                        asr_model = load_asr(model_name, local_only=True)
                    else:
                        logger.info(f"Worker {job_id}: Attempting to download model (XET should be disabled)...")
                        asr_model = load_asr(model_name, local_only=False)
                
                    load_complete.set()
                    load_duration = time.time() - load_start_time
                    logger.info(f"Worker {job_id}: ASR model loaded after {load_duration:.1f}s")
                
                except RuntimeError as runtime_error:
                    error_str = str(runtime_error)
                
                    # se for erro de rede/XET tenta cache only
                    if ("cas" in error_str.lower() or "xet" in error_str.lower() or "xethub" in error_str.lower()
                        or "no route to host" in error_str.lower() or "max retries" in error_str.lower()
                        or "timeout" in error_str.lower() or "connection" in error_str.lower()):
                
                        logger.warning(f"Worker {job_id}: Network/XET error, trying cache only...")
                        try:
                            asr_model = load_asr(model_name, local_only=True)
                            load_complete.set()
                            load_duration = time.time() - load_start_time
                            logger.info(f"Worker {job_id}: Loaded ASR from cache after {load_duration:.1f}s")
                        except Exception as cache_error:
                            error_msg = (
                                f"Failed to download model and cache load failed. "
                                f"Ensure model '{model_name}' is cached in HF_HOME. "
                                f"Original error: {error_str[:300]}"
                            )
                            logger.error(f"Worker {job_id}: {error_msg}")
                            logger.exception(cache_error)
                            _set_job(job_id, {"status": "error", "error": error_msg})
                            _log_event(job_id, "Network error: model not cached and download failed", stage="error")
                            return
                    else:
                        logger.exception(f"Worker {job_id}: RuntimeError loading ASR model: {runtime_error}")
                        raise
                
                except Exception as model_load_error:
                    logger.exception(f"Worker {job_id}: Error loading ASR model: {model_load_error}")
                    raise
                
                logger.info(f"Worker {job_id}: ASR model loaded successfully, type: {type(asr_model)}")

                _log_event(job_id, "Transcribing...", stage="transcribe", progress=35)
                logger.info(f"Worker {job_id}: Starting transcription (lang={lang})")
                logger.info(f"Worker {job_id}: Audio file path: {wav_path}, exists: {wav_path.exists()}, size: {wav_path.stat().st_size if wav_path.exists() else 'N/A'} bytes")
                logger.info(f"Worker {job_id}: About to call asr_model.transcribe() - this may take a while...")
                try:
                    result = asr_model.transcribe(str(wav_path), language=None if lang == "auto" else lang)
                    logger.info(f"Worker {job_id}: asr_model.transcribe() returned successfully")
                except Exception as transcribe_error:
                    logger.exception(f"Worker {job_id}: Error during transcription: {transcribe_error}")
                    raise
                logger.info(f"Worker {job_id}: Transcription completed, detected language: {result.get('language')}, segments count: {len(result.get('segments', []))}")

                # Sem diarização
                if not diarize:
                    text = (result.get("text") or "").strip()
                    out_txt = RESULTS_DIR / f"{job_id}.txt"
                    out_txt.write_text(text + "\n", encoding="utf-8")
                    logger.info(f"Worker {job_id}: Result saved to {out_txt} (no diarization)")
                    _set_job(job_id, {
                        "status": "done",
                        "finished_at": time.time(),
                        "result_txt": str(out_txt),
                        "diarization": False,
                        "language": result.get("language"),
                    })
                    _log_event(job_id, "Done (no diarization).", stage="done", progress=100)
                    logger.info(f"Worker {job_id}: Job completed successfully (no diarization)")
                    return

                # Diarização exige token
                if not HF_TOKEN:
                    logger.warning(f"Worker {job_id}: HF_TOKEN not set, skipping diarization")
                    text = (result.get("text") or "").strip()
                    out_txt = RESULTS_DIR / f"{job_id}.txt"
                    out_txt.write_text(text + "\n", encoding="utf-8")
                    logger.info(f"Worker {job_id}: Result saved to {out_txt} (diarization skipped)")
                    _set_job(job_id, {
                        "status": "done",
                        "finished_at": time.time(),
                        "result_txt": str(out_txt),
                        "diarization": False,
                        "language": result.get("language"),
                        "note": "HF_TOKEN not set, diarization skipped.",
                    })
                    _log_event(job_id, "HF_TOKEN not set → returning transcript without speakers.", stage="done", progress=100)
                    logger.info(f"Worker {job_id}: Job completed (diarization skipped)")
                    return

                # =========================
                # Diarização (robusta)
                # =========================
                DIARIZATION_MODEL = os.getenv("DIARIZATION_MODEL", "pyannote/speaker-diarization-3.1")
                
                _log_event(job_id, "Running diarization...", stage="diarize", progress=55)
                logger.info(f"Worker {job_id}: Starting diarization")
                
                diarize_segments = None
                
                # 1) Tentar whisperx DiarizationPipeline (se existir)
                if DiarizationPipeline is not None:
                    try:
                        logger.info(f"Worker {job_id}: Trying whisperx DiarizationPipeline...")
                        diarize_model = DiarizationPipeline(use_auth_token=HF_TOKEN, device=DEVICE)
                        
                        # Se o modelo ficou None (teu erro atual), força fallback
                        if getattr(diarize_model, "model", None) is None:
                            raise RuntimeError("whisperx DiarizationPipeline loaded model=None")
                        
                        diarize_segments = diarize_model(str(wav_path))
                        
                        # valida output
                        if isinstance(diarize_segments, pd.DataFrame):
                            if diarize_segments.empty:
                                raise RuntimeError("whisperx diarization returned empty dataframe")
                        elif isinstance(diarize_segments, dict):
                            if not diarize_segments.get("segments"):
                                raise RuntimeError("whisperx diarization returned empty segments")
                        else:
                            raise RuntimeError("whisperx diarization returned unexpected format")
                        
                        # Log segment count
                        if isinstance(diarize_segments, pd.DataFrame):
                            logger.info(f"Worker {job_id}: Diarization OK (whisperx), segments: {len(diarize_segments)}")
                        else:
                            logger.info(f"Worker {job_id}: Diarization OK (whisperx), segments: {len(diarize_segments.get('segments', []))}")
                        
                    except Exception as e:
                        logger.warning(f"Worker {job_id}: whisperx diarization failed -> fallback pyannote. Reason: {e}")
                        diarize_segments = None
                
                # 2) Fallback pyannote direto (mais estável)
                if diarize_segments is None:
                    try:
                        import torch
                        from pyannote.audio import Pipeline
                        
                        logger.info(f"Worker {job_id}: Loading pyannote pipeline: {DIARIZATION_MODEL}")
                        pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, use_auth_token=HF_TOKEN)
                        
                        # manda para GPU/CPU
                        pipeline.to(torch.device(DEVICE))
                        
                        diarization = pipeline(str(wav_path))
                        
                        segments = []
                        for turn, _, speaker in diarization.itertracks(yield_label=True):
                            segments.append({
                                "start": float(turn.start),
                                "end": float(turn.end),
                                "speaker": str(speaker),
                            })
                        
                        diarize_segments = {"segments": segments}
                        logger.info(f"Worker {job_id}: Diarization OK (pyannote), segments: {len(segments)}")
                        
                    except Exception as e:
                        # ✅ em vez de crashar, devolve só transcript sem speakers
                        logger.exception(f"Worker {job_id}: Diarization failed completely: {e}")
                        _log_event(job_id, "Diarization failed → returning transcript without speakers.", stage="done", progress=100)
                        
                        text = (result.get("text") or "").strip()
                        out_txt = RESULTS_DIR / f"{job_id}.txt"
                        out_txt.write_text(text + "\n", encoding="utf-8")
                        
                        _set_job(job_id, {
                            "status": "done",
                            "finished_at": time.time(),
                            "result_txt": str(out_txt),
                            "diarization": False,
                            "language": result.get("language"),
                            "note": f"Diarization failed: {e}",
                        })
                        return

                # Alinhamento
                _log_event(job_id, "Loading align model...", stage="load_align", progress=70)
                detected_lang = result.get("language", "unknown")
                logger.info(f"Worker {job_id}: Loading alignment model for language: {detected_lang}")
                logger.info(f"Worker {job_id}: About to call whisperx.load_align_model() - this may take a while (downloading from Hugging Face if not cached)...")
                try:
                    align_model, metadata = whisperx.load_align_model(language_code=detected_lang, device=DEVICE)
                    logger.info(f"Worker {job_id}: Alignment model loaded successfully")
                except RuntimeError as runtime_error:
                    error_str = str(runtime_error)
                    if "CAS service error" in error_str or "Request failed" in error_str or "retries" in error_str:
                        error_msg = f"Failed to download alignment model from Hugging Face Hub. Network issue. Error: {error_str[:200]}"
                        logger.error(f"Worker {job_id}: {error_msg}")
                        _set_job(job_id, {"status": "error", "error": error_msg})
                        _log_event(job_id, f"Network error downloading alignment model", stage="error")
                        return
                    else:
                        logger.exception(f"Worker {job_id}: RuntimeError loading alignment model: {runtime_error}")
                        raise
                except Exception as align_load_error:
                    error_str = str(align_load_error)
                    if "connection" in error_str.lower() or "network" in error_str.lower() or "timeout" in error_str.lower():
                        error_msg = f"Network error while loading alignment model: {error_str[:200]}"
                        logger.error(f"Worker {job_id}: {error_msg}")
                        _set_job(job_id, {"status": "error", "error": error_msg})
                        _log_event(job_id, f"Network error: {error_str[:100]}", stage="error")
                        return
                    else:
                        logger.exception(f"Worker {job_id}: Error loading alignment model: {align_load_error}")
                        raise

                _log_event(job_id, "Aligning...", stage="align", progress=78)
                logger.info(f"Worker {job_id}: Starting alignment, input segments: {len(result.get('segments', []))}")
                logger.info(f"Worker {job_id}: About to call whisperx.align() - this may take a while...")
                try:
                    result_aligned = whisperx.align(result["segments"], align_model, metadata, str(wav_path), DEVICE)
                    logger.info(f"Worker {job_id}: Alignment completed, aligned segments: {len(result_aligned.get('segments', []))}")
                except Exception as align_error:
                    logger.exception(f"Worker {job_id}: Error during alignment: {align_error}")
                    raise

                # Atribuir speakers
                _log_event(job_id, "Assigning speakers...", stage="assign_speakers", progress=88)
                logger.info(f"Worker {job_id}: Assigning speakers to segments")
                
                # Converter diarização para DataFrame no formato que whisperx quer
                if isinstance(diarize_segments, dict) and "segments" in diarize_segments:
                    diarize_df = pd.DataFrame(diarize_segments["segments"])
                elif isinstance(diarize_segments, list):
                    diarize_df = pd.DataFrame(diarize_segments)
                elif isinstance(diarize_segments, pd.DataFrame):
                    diarize_df = diarize_segments  # caso já venha DataFrame
                else:
                    raise ValueError(f"Unexpected diarize_segments type: {type(diarize_segments)}")
                
                # Garantir que tem colunas certas
                if "end" not in diarize_df.columns and "stop" in diarize_df.columns:
                    diarize_df = diarize_df.rename(columns={"stop": "end"})
                
                logger.info(f"Worker {job_id}: Diarize segments: {len(diarize_df)}, Aligned segments: {len(result_aligned.get('segments', []))}")
                logger.info(f"Worker {job_id}: About to call whisperx.assign_word_speakers()...")
                try:
                    result_with_speakers = whisperx.assign_word_speakers(diarize_df, result_aligned)
                    logger.info(f"Worker {job_id}: Speaker assignment completed, final segments: {len(result_with_speakers.get('segments', []))}")
                except Exception as assign_error:
                    logger.exception(f"Worker {job_id}: Error assigning speakers: {assign_error}")
                    raise

                segments = result_with_speakers.get("segments", [])
                pretty = format_segments_with_speakers(segments)

                out_txt = RESULTS_DIR / f"{job_id}.txt"
                out_txt.write_text(pretty + "\n", encoding="utf-8")
                logger.info(f"Worker {job_id}: Result saved to {out_txt}")

                _set_job(job_id, {
                    "status": "done",
                    "finished_at": time.time(),
                    "result_txt": str(out_txt),
                    "diarization": True,
                    "language": result.get("language"),
                })
                _log_event(job_id, "Done.", stage="done", progress=100)
                logger.info(f"Worker {job_id}: Job completed successfully")

            except subprocess.CalledProcessError as e:
                error_msg = f"ffmpeg failed: {str(e)}"
                logger.exception(f"Worker {job_id}: {error_msg}")
                _set_job(job_id, {"status": "error", "error": error_msg})
                _log_event(job_id, "ffmpeg failed.", stage="error")
            except Exception as e:
                error_msg = str(e)
                logger.exception(f"Worker {job_id}: Unexpected error: {error_msg}")
                _set_job(job_id, {"status": "error", "error": error_msg})
                _log_event(job_id, f"Error: {e}", stage="error")
    except Exception as e:
        # Erro antes de entrar no lock ou ao adquirir o lock
        error_msg = f"Worker failed to start: {str(e)}"
        logger.exception(f"Worker {job_id}: {error_msg}")
        _set_job(job_id, {"status": "error", "error": error_msg})
        _log_event(job_id, f"Worker failed: {e}", stage="error")


# =========================
# Endpoints
# =========================
@app.get("/health")
def health():
    return {
        "ok": True,
        "videos_dir": str(VIDEOS_DIR),
        "videos_dir_exists": VIDEOS_DIR.exists(),
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "hf_token_set": bool(HF_TOKEN),
    }


@app.post("/jobs")
def create_job(req: CreateJobRequest):
    logger.info(f"Creating job for file: {req.filename} (lang={req.lang}, model={req.model}, diarize={req.diarize})")
    
    if not VIDEOS_DIR.exists():
        error_msg = "Videos directory not mounted/available"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    src = (VIDEOS_DIR / req.filename).resolve()
    if not str(src).startswith(str(VIDEOS_DIR)) or not src.exists():
        error_msg = f"File not found in videos directory: {req.filename} (checked: {src})"
        logger.error(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)

    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "filename": req.filename,
        "lang": req.lang,
        "model": req.model,
        "diarize": req.diarize,
        "status": "queued",
        "created_at": time.time(),
        "logs": [],
    }
    _set_job(job_id, job)
    _log_event(job_id, "Queued.", stage="queued", progress=0)
    logger.info(f"Job {job_id} created and queued")

    t = threading.Thread(target=_worker, args=(job_id, req.filename, req.lang, req.model, req.diarize), daemon=True)
    t.start()
    logger.info(f"Worker thread started for job {job_id}, thread alive: {t.is_alive()}")

    return {"job_id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    try:
        return _get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@app.get("/jobs/{job_id}/result")
def get_result(job_id: str):
    try:
        job = _get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail=f"Job not done. Status: {job.get('status')}")

    p = Path(job.get("result_txt", ""))
    if not p.exists():
        raise HTTPException(status_code=500, detail="Result missing on disk")

    return JSONResponse({
        "job_id": job_id,
        "diarization": job.get("diarization", False),
        "language": job.get("language"),
        "text": p.read_text(encoding="utf-8"),
    })


@app.get("/jobs/{job_id}/events")
def job_events(job_id: str):
    # Server-Sent Events: stream de eventos enquanto o job corre
    try:
        _ = _get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    def event_stream():
        last_idx = 0
        while True:
            # termina quando done/error
            job = _get_job(job_id)
            status = job.get("status")

            with JOB_EVENTS_LOCK:
                evts = JOB_EVENTS.get(job_id, [])
                new = evts[last_idx:]
                last_idx += len(new)

            for e in new:
                yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"

            if status in ("done", "error"):
                yield f"data: {json.dumps({'stage':'final','status':status}, ensure_ascii=False)}\n\n"
                break

            time.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")