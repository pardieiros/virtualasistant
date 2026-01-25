Perfeito 👍
Aqui vai apenas a documentação das APIs, limpa e direta, em Markdown, sem arquitetura, sem infra.

⸻


# 📡 Transcribe + Diarize API — Documentação de Endpoints

Base URL:

http://:8967

---

## 🔍 Health Check

### `GET /health`

Verifica o estado da API, GPU, pasta de vídeos e diarização.

#### Resposta 200
```json
{
  "ok": true,
  "videos_dir": "/srv/smb/videos",
  "videos_dir_exists": true,
  "device": "cuda",
  "compute_type": "float16",
  "hf_token_set": true
}


⸻

🎬 Criar Job de Transcrição

POST /jobs

Cria um job assíncrono a partir de um ficheiro existente na pasta de vídeos.

Body (JSON)

{
  "filename": "Video 5.mp4",
  "lang": "pt",
  "model": "small",
  "diarize": true
}

Campos

Campo	Tipo	Obrigatório	Descrição
filename	string	✅	Nome do ficheiro em /srv/smb/videos
lang	string	❌	pt, en ou auto (default: pt)
model	string	❌	tiny, base, small, medium, large-v2
diarize	boolean	❌	Ativa diarização (true por defeito)

Resposta 200

{
  "job_id": "UUID",
  "status": "queued"
}

Erros
	•	404 — ficheiro não encontrado
	•	500 — pasta de vídeos indisponível

⸻

📄 Obter Estado do Job

GET /jobs/{job_id}

Obtém o estado atual e logs do job.

Resposta 200

{
  "id": "UUID",
  "filename": "Video 5.mp4",
  "status": "processing",
  "lang": "pt",
  "model": "small",
  "diarize": true,
  "created_at": 1705870000.12,
  "started_at": 1705870005.45,
  "logs": [
    {
      "ts": 1705870006.12,
      "stage": "extract_audio",
      "progress": 15,
      "message": "Extracting audio (ffmpeg)..."
    }
  ]
}

Estados possíveis
	•	queued
	•	processing
	•	done
	•	error

⸻

📡 Progresso em Tempo Real (SSE)

GET /jobs/{job_id}/events

Stream de eventos Server-Sent Events (SSE) com progresso do job.

Exemplo (terminal)

curl -N http://localhost:8967/jobs/<JOB_ID>/events

Eventos enviados

{
  "ts": 1705870010.44,
  "stage": "transcribe",
  "progress": 35,
  "message": "Transcribing..."
}

Etapas (stage)
	•	queued
	•	copy
	•	extract_audio
	•	load_asr
	•	transcribe
	•	diarize
	•	load_align
	•	align
	•	assign_speakers
	•	done
	•	error

O stream termina automaticamente em done ou error.

⸻

📝 Obter Resultado Final

GET /jobs/{job_id}/result

Devolve o texto final com identificação de oradores.

Condições
	•	Só disponível quando status = done

Resposta 200

{
  "job_id": "UUID",
  "diarization": true,
  "language": "pt",
  "text": "[00.00-05.12] User1: Bom dia...\n[05.13-10.40] User2: Obrigado..."
}

Erros
	•	404 — job inexistente
	•	409 — job ainda não terminado
	•	500 — resultado não encontrado em disco

⸻

👥 Diarização
	•	Os speakers são normalizados automaticamente:
	•	SPEAKER_00 → User1
	•	SPEAKER_01 → User2
	•	Requer HF_TOKEN configurado
	•	Se não existir token:
	•	A API devolve apenas texto contínuo (sem speakers)

⸻

⚠️ Notas Importantes
	•	A API não aceita uploads
	•	Apenas 1 job simultâneo
	•	Ficheiros grandes são suportados
	•	Progresso é por etapas (não percentagem real de áudio)

