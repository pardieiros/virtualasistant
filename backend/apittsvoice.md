# Jarvas TTS (Piper) – Documentação de Uso

Servidor de Text-to-Speech (TTS) baseado em **Piper** a correr na máquina:

- **IP:** `192.168.1.73`
- **Porta:** `8010`
- **Base URL:** `http://192.168.1.73:8010`
- **Modelo:** PT-PT (voz masculina, “tugão medium”)

---

## 1. Visão Geral

O `jarvas-tts` é um microserviço HTTP que recebe texto em português e devolve um ficheiro de áudio **WAV** com voz PT-PT, usando o motor **Piper**.

Características:

- 100% local (sem cloud)
- Rápido e leve
- Não guarda ficheiros em disco (resposta é sempre em streaming)
- Ideal para ser chamado pelo backend do Jarvas (ou qualquer outra app)

---

## 2. Endpoints

### `POST /api/tts/`

Gera áudio a partir de texto.

- **URL completa:**  
  `http://192.168.1.73:8010/api/tts/`
- **Método:** `POST`
- **Content-Type:** `application/json`
- **Body:**

```json
{
  "text": "Olá, eu sou o Jarvas a falar em português de Portugal."
}