# Memória Vetorial com pgvector - Guia de Setup

Este guia explica como configurar a memória vetorial para o assistente Ollama usando pgvector no PostgreSQL.

## Visão Geral

O sistema de memória permite que o assistente:
- Lembre-se de interações passadas (compras, eventos, preferências)
- Forneça respostas contextualizadas baseadas em memórias anteriores
- Aprenda preferências do utilizador ao longo do tempo

A implementação usa **pgvector**, uma extensão do PostgreSQL que permite armazenar e pesquisar vetores (embeddings) diretamente na base de dados.

## Pré-requisitos

- PostgreSQL 11+ instalado
- Acesso de superutilizador ao PostgreSQL (para criar a extensão)
- Python 3.8+
- Ollama com modelo que suporta embeddings

## Passo 1: Instalar pgvector no PostgreSQL

### Opção A: PostgreSQL local

Se tens PostgreSQL instalado localmente:

```bash
# Conectar ao PostgreSQL
psql -U postgres -d personalassistance

# Criar a extensão
CREATE EXTENSION IF NOT EXISTS vector;

# Verificar se foi criada
\dx vector
```

### Opção B: PostgreSQL via Docker

Se usas PostgreSQL em Docker:

```bash
# Entrar no container
docker exec -it <postgres-container-name> psql -U postgres -d personalassistance

# Criar a extensão
CREATE EXTENSION IF NOT EXISTS vector;
```

### Opção C: PostgreSQL remoto

Se tens um servidor PostgreSQL remoto, conecta-te e executa:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Nota:** Se não tiveres privilégios de superutilizador, pede ao administrador da base de dados para executar este comando.

## Passo 2: Instalar dependências Python

```bash
cd backend
source venv/bin/activate  # ou o teu ambiente virtual
pip install -r requirements.txt
```

Isto vai instalar o `pgvector==0.2.4` que é necessário para o Django trabalhar com vetores.

## Passo 3: Executar Migrations

```bash
cd backend
source venv/bin/activate
python manage.py migrate
```

Isto vai:
- Criar a tabela `assistant_memory` com o campo `embedding` (vector)
- Criar os índices necessários

## Passo 4: Verificar se Ollama suporta Embeddings

O sistema usa a API de embeddings do Ollama. Verifica se o teu modelo suporta:

```bash
curl http://localhost:11434/api/embeddings -d '{
  "model": "marco-assistente",
  "prompt": "teste"
}'
```

Se retornar um array de números (o embedding), está tudo bem!

## Como Funciona

### 1. Salvamento Automático de Memórias

Quando o utilizador interage com o assistente:
- **Ações executadas** (adicionar item à lista, criar evento) são automaticamente guardadas como memórias
- **Preferências mencionadas** (ex: "gosto de...", "nunca...") são guardadas como memórias de preferência
- Cada memória recebe um **embedding vetorial** gerado pelo Ollama

### 2. Recuperação de Memórias

Quando o utilizador faz uma pergunta:
- O sistema gera um embedding da pergunta
- Pesquisa memórias similares usando **similaridade de cosseno**
- As memórias mais relevantes são incluídas no contexto do Ollama

### 3. Tipos de Memória

- **shopping**: Memórias sobre compras (ex: "Adicionei leite à lista")
- **agenda**: Memórias sobre eventos (ex: "Criei evento: Reunião")
- **preference**: Preferências do utilizador (ex: "Gosto de café")
- **fact**: Factos gerais (ex: notas guardadas)
- **interaction**: Interações gerais
- **other**: Outros tipos

## Estrutura da Base de Dados

A tabela `assistant_memory` contém:
- `id`: ID único
- `user_id`: Utilizador dono da memória
- `content`: Conteúdo da memória (texto)
- `embedding`: Vetor de 768 dimensões (gerado pelo Ollama)
- `memory_type`: Tipo de memória
- `metadata`: JSON com metadados adicionais
- `importance`: Score de importância (0.0 a 1.0)
- `created_at`, `updated_at`: Timestamps

## Troubleshooting

### Erro: "extension 'vector' does not exist"

**Solução:** A extensão pgvector não foi instalada no PostgreSQL. Executa:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Erro: "permission denied to create extension"

**Solução:** Não tens privilégios de superutilizador. Pede ao administrador da base de dados para executar o comando.

### Erro: "Failed to generate embedding"

**Solução:** Verifica se:
1. O Ollama está a correr
2. O modelo configurado suporta embeddings
3. A URL do Ollama está correta em `settings.py`

### Memórias não estão a ser recuperadas

**Solução:** Verifica se:
1. As memórias têm embeddings (campo `embedding` não é NULL)
2. O modelo de embeddings está a gerar vetores com 768 dimensões
3. Os logs do Django para erros

## Verificar Memórias no Admin

Podes ver e gerir memórias no Django Admin:
1. Acede a `/admin/`
2. Vai a "Memories"
3. Vês todas as memórias guardadas
4. Podes editar ou eliminar memórias manualmente

## Limpar Memórias Antigas

Para limpar memórias antigas ou irrelevantes:

```python
from assistant.models import Memory
from django.utils import timezone
from datetime import timedelta

# Eliminar memórias com mais de 1 ano
old_memories = Memory.objects.filter(
    created_at__lt=timezone.now() - timedelta(days=365)
)
old_memories.delete()
```

## Performance

- **Índices:** O pgvector cria automaticamente índices HNSW para pesquisas rápidas
- **Dimensões:** Os embeddings têm 768 dimensões (padrão do Ollama)
- **Limite de pesquisa:** Por padrão, pesquisa as 5 memórias mais relevantes

## Próximos Passos

- Ajustar a importância das memórias baseado no feedback do utilizador
- Implementar limpeza automática de memórias antigas
- Adicionar mais tipos de memória conforme necessário
- Melhorar a extração de memórias usando LLM para identificar informações importantes

