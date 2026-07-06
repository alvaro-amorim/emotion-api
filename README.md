# Audio Emotion API

API **local-first** em Python para receber arquivos de áudio, transcrever fala, extrair métricas acústicas, interpretar sinais emocionais e gerar um contexto pronto para ser usado por outros agentes de IA.

> Este projeto é um MVP experimental. A análise emocional é interpretativa e probabilística; não deve ser tratada como diagnóstico psicológico, clínico ou verdade absoluta.

## Projetos relacionados

Este repositório é a API principal do ecossistema:

- **Audio Emotion API** — este repositório. Recebe áudio, transcreve, calcula métricas acústicas, interpreta emoção/intenção e retorna um JSON estruturado.
- **[audio-emotion-client-demo](https://github.com/alvaro-amorim/audio-emotion-client-demo)** — app cliente de demonstração que consome esta API, monta um prompt emocionalmente contextualizado e envia para uma LLM.

Fluxo entre os dois projetos:

```txt
Usuário envia/grava áudio
        ↓
audio-emotion-client-demo
        ↓  POST /v1/analyze-audio + X-API-Key
Audio Emotion API
        ↓
Transcrição + métricas + emoção + contexto para IA
        ↓
audio-emotion-client-demo monta prompt e chama uma LLM
```

## Propósito do projeto

O objetivo deste MVP foi explorar uma camada intermediária entre áudio humano e agentes de IA. Muitas aplicações de IA recebem apenas texto transcrito e perdem sinais importantes da fala, como ritmo, pausas, volume, hesitação, urgência e ênfase.

A **Audio Emotion API** tenta preencher essa lacuna retornando uma transcrição enriquecida com contexto emocional e sinais acústicos, permitindo que outro agente de IA responda de forma mais adequada ao estado provável do usuário.

Exemplo de uso:

```txt
Áudio do usuário
↓
Transcrição real
↓
Métricas acústicas reais
↓
Análise emocional interpretativa
↓
Contexto recomendado para outro agente de IA
```

## Principais recursos

- Upload de áudio em `.mp3`, `.wav`, `.m4a`, `.webm` e `.ogg`.
- Gravação de áudio pelo navegador na interface local.
- Conversão com FFmpeg para WAV mono 16 kHz.
- Métricas acústicas reais:
  - duração;
  - volume médio;
  - pico de volume;
  - variação de volume;
  - dynamic range;
  - quantidade e proporção de silêncio;
  - eventos de pico;
  - timeline de volume;
  - warnings de qualidade.
- Transcrição local real com `faster-whisper`.
- Áudio otimizado separadamente para transcrição, sem alterar o áudio usado nas métricas acústicas.
- Normalização de idioma `pt-BR` para `pt` no Whisper.
- Cálculo de ritmo de fala e palavras por minuto.
- Análise emocional interpretativa com:
  - heurísticas locais;
  - Cohere opcional;
  - fallback local quando Cohere estiver desativada ou indisponível.
- Transcrição comentada com marcações do tipo:

```txt
[emoção: preocupação | tom: hesitante | observação: pausa longa antes da frase]
```

- Debug emocional e comparação entre Cohere e fallback local.
- Feedback humano para corrigir/validar interpretações.
- `learning_examples` locais para reutilizar feedbacks aprovados.
- Ranking simples de exemplos parecidos por texto e métricas acústicas.
- Exportação de dataset local em JSONL.
- API Key local opcional via `X-API-Key` para simular consumo por apps externos.

## Stack

- Python 3.11+
- FastAPI
- SQLModel
- SQLite
- FFmpeg
- NumPy
- faster-whisper
- Cohere SDK opcional
- HTML, CSS e JavaScript puro
- pytest/httpx

## Arquitetura resumida

```txt
POST /v1/analyze-audio
        ↓
Validação do arquivo
        ↓
Salvamento temporário
        ↓
FFmpeg → WAV padronizado
        ↓
Métricas acústicas reais
        ↓
WAV otimizado para transcrição
        ↓
faster-whisper
        ↓
Análise emocional local + Cohere opcional
        ↓
Persistência SQLite
        ↓
JSON final para agentes de IA
```

## Pré-requisitos

Instale o FFmpeg e garanta que ele esteja disponível no `PATH`:

```bash
ffmpeg -version
```

Também é necessário Python 3.11+.

## Instalação local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

A primeira execução da transcrição pode baixar o modelo configurado do `faster-whisper`.

## Configuração

Crie um `.env` a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Variáveis principais:

```env
APP_ENV=development
APP_VERSION=0.5.6
DEFAULT_LANGUAGE=pt-BR

DATABASE_URL=sqlite:///./data/audio_emotion.db

ALLOWED_AUDIO_EXTENSIONS=mp3,wav,m4a,webm,ogg
MAX_AUDIO_DURATION_SECONDS=600
MAX_AUDIO_SIZE_MB=100

TRANSCRIPTION_PROVIDER=local
LOCAL_TRANSCRIPTION_ENGINE=faster-whisper
WHISPER_MODEL_SIZE=tiny
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_BEAM_SIZE=5
WHISPER_BEST_OF=5
WHISPER_TEMPERATURE=0
WHISPER_VAD_FILTER=true
WHISPER_CONDITION_ON_PREVIOUS_TEXT=false

USE_COHERE=true
COHERE_API_KEY=
COHERE_CHAT_MODEL=command-a-03-2025
EMOTION_ANALYSIS_PROVIDER=hybrid

REQUIRE_API_KEY=true
LOCAL_API_KEY=dev-local-key-change-me
API_KEY_HEADER_NAME=X-API-Key
ALLOWED_CLIENT_ORIGINS=http://127.0.0.1:8020,http://localhost:8020
AUDIO_EMOTION_API_URL=http://127.0.0.1:8014
```

Nunca versionar `.env` ou chaves reais. O arquivo `.env.example` deve conter apenas valores de exemplo.

Para rodar sem Cohere:

```env
USE_COHERE=false
```

Nesse caso, a análise emocional continua funcionando com fallback local.

## Como rodar

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8014
```

Abra a interface local:

```txt
http://127.0.0.1:8014
```

Endpoints úteis:

```txt
GET  /health
GET  /v1/system/status
POST /v1/analyze-audio
GET  /v1/analyses
GET  /v1/learning/examples
```

## Consumo com API Key

Quando `REQUIRE_API_KEY=true`, os endpoints sensíveis exigem o header configurado:

```txt
X-API-Key: dev-local-key-change-me
```

Exemplo com `curl.exe` no Windows:

```cmd
curl.exe -X POST "http://127.0.0.1:8014/v1/analyze-audio" ^
  -H "X-API-Key: dev-local-key-change-me" ^
  -F "file=@tests/fixtures/audio/ptbr_01_calmo_normal.m4a"
```

Resposta resumida esperada:

```json
{
  "analysis_id": "uuid",
  "status": {
    "acoustic_metrics_status": "real",
    "transcription_status": "real",
    "emotion_status": "real"
  },
  "transcription": {
    "text": "texto transcrito..."
  },
  "emotion_summary": {
    "primary_emotion": "calma",
    "confidence_score": 0.82
  },
  "recommended_context_for_ai_agent": {
    "response_strategy": "responder com calma e clareza"
  }
}
```

Se Cohere estiver indisponível ou desativada, `emotion_status` pode retornar `fallback_local`.

## Uso com o app cliente demo

Para testar o ecossistema completo:

1. Rode este projeto em `http://127.0.0.1:8014`.
2. Configure `REQUIRE_API_KEY=true` e `LOCAL_API_KEY=dev-local-key-change-me`.
3. Rode o repositório **[audio-emotion-client-demo](https://github.com/alvaro-amorim/audio-emotion-client-demo)** em `http://127.0.0.1:8020`.
4. Envie ou grave um áudio pelo app cliente.
5. O app cliente enviará o áudio para esta API, receberá o contexto emocional e usará esse contexto para gerar uma resposta com LLM.

## Formato de saída

A resposta da API foi pensada para ser consumida por outro agente de IA. Os campos principais incluem:

- `analysis_id`
- `status`
- `metadata`
- `transcription.text`
- `transcription.segments`
- `transcription.words`
- `transcription_quality`
- `acoustic_metrics`
- `emotion_summary`
- `annotated_transcription`
- `important_observations`
- `recommended_context_for_ai_agent`
- `emotion_debug`
- `emotion_comparison`
- `learning_examples_used`

## Qualidade da transcrição

A API gera dois arquivos processados:

- `*_16khz_mono.wav`: usado para métricas acústicas reais.
- `*_16khz_mono_transcription.wav`: usado apenas para transcrição, com filtros leves de inteligibilidade.

O JSON retorna `transcription_quality`, incluindo:

- idioma usado;
- engine/modelo;
- arquivo usado na transcrição;
- confiança média;
- warnings de silêncio, clipping, áudio curto ou baixa confiança.

Para melhorar os resultados:

- fale perto do microfone;
- evite ruído e eco;
- evite volume estourado/clipping;
- use microfone externo quando possível;
- teste `WHISPER_MODEL_SIZE=small` se `tiny` errar demais.

## Feedback e aprendizado local

A aplicação não treina a Cohere e não faz fine-tuning.

O aprendizado atual é baseado em memória local:

- o usuário pode corrigir uma análise;
- o feedback pode virar um `learning_example`;
- exemplos aprovados podem influenciar análises futuras;
- o ranking usa sinais textuais, acústicos e recência;
- a Cohere pode receber exemplos parecidos como contexto, mas eles não forçam a resposta.

Embeddings e RAG vetorial ainda estão fora do escopo atual.

## Dados locais

Arquivos e dados gerados localmente ficam fora do Git:

- `.env`
- `.venv/`
- `data/`
- `storage/`
- `exports/`
- `*.db`, `*.sqlite`, `*.sqlite3`
- arquivos reais de áudio em `tests/fixtures/audio/*`

Mantenha apenas documentação/arquivos de exemplo seguros no repositório.

## Exportar dataset local

```powershell
python scripts/export_learning_dataset.py
python scripts/export_learning_dataset.py --approved-only
```

O arquivo padrão é:

```txt
exports/learning_dataset.jsonl
```

## Limpeza local

Ver o que seria apagado:

```powershell
python scripts/cleanup_local_data.py --dry-run
```

Limpar dados locais:

```powershell
python scripts/cleanup_local_data.py --yes
```

## Testes

```powershell
python -m pytest
python -m pytest -m real_audio
```

Os testes marcados como `real_audio` pulam de forma controlada se as fixtures locais não existirem.

Scripts úteis:

```powershell
python scripts/validate_audio_fixtures.py
python scripts/validate_audio_fixtures.py --no-cohere
python scripts/smoke_api_key_client.py
```

## Limitações atuais

- MVP local-first, não SaaS em produção.
- Uma única API Key local, sem usuários, billing ou rate limit.
- Análise emocional interpretativa/probabilística.
- Sem diarização de múltiplos falantes.
- Sem análise por sílaba/fonema.
- Sem embeddings ou busca vetorial.
- A qualidade da transcrição depende do áudio, microfone e modelo Whisper configurado.

## Roadmap

- Embeddings opcionais para melhorar busca de exemplos parecidos.
- Exportação mais robusta de dataset de feedback.
- Melhor calibração de pesos heurísticos.
- Processamento assíncrono para áudios maiores.
- API keys multiusuário e rate limit.
- Deploy com container e storage persistente.

## Aviso

Este projeto foi criado para estudo, portfólio e validação técnica de produto. Ele não substitui avaliação humana e não deve ser usado para decisões sensíveis sem revisão e validação adequada.
