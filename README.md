# Audio Emotion API

API local-first em Python para receber áudio, calcular métricas acústicas reais, transcrever localmente, gerar análise emocional interpretativa e salvar o resultado em SQLite.

## Estado Atual

Rodada 5.5:

- Upload e gravação pelo navegador funcionando.
- Conversão real de áudio com FFmpeg para WAV mono 16 kHz PCM.
- Métricas acústicas reais calculadas a partir do áudio enviado.
- Transcrição local real com `faster-whisper`.
- Análise emocional interpretativa real usando heurísticas locais.
- Cohere opcional como motor contextual quando configurada.
- Fallback local automático quando Cohere está desativada, sem chave ou falha.
- Transcrição comentada com colchetes gerada a partir do texto real.
- Debug emocional no JSON e na interface.
- Comparação entre fallback local e Cohere quando a Cohere é usada.
- Feedback e `learning_examples` continuam funcionando.
- Exemplos aprovados sao ranqueados por similaridade simples de texto + metricas.
- O fallback local usa exemplos parecidos para reforcar ou ajustar a interpretacao.
- O prompt da Cohere recebe os melhores exemplos parecidos quando disponiveis.
- Pesos heuristicos estao organizados e configuraveis por `.env`.
- `learning_examples` guardam previsão original, correção, tom, motivo e snapshot de métricas.
- `/health` e `/v1/system/status` mostram diagnostico local seguro para evitar confusao com servidores antigos.
- A interface mostra status do sistema, historico recente e gestao simples de `learning_examples`.
- `learning_examples` podem ser filtrados e desativados via API.
- O dataset local de aprendizado pode ser exportado em JSONL.
- Dados locais de teste podem ser limpos com script seguro.
- Embeddings, fine-tuning, diarização e análise por sílaba ainda não existem.

## Stack

- Python 3.11
- FastAPI
- SQLModel
- SQLite
- FFmpeg instalado no sistema
- NumPy
- faster-whisper
- Cohere opcional
- HTML, CSS e JavaScript puro para a interface local
- pytest/httpx

## Pré-requisitos

O FFmpeg precisa estar instalado e disponível no `PATH`.

```bash
ffmpeg -version
```

## Instalação

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

A primeira execução da transcrição pode baixar o modelo do `faster-whisper` e demorar mais.

## Configuração

Copie `.env.example` para `.env` e ajuste se necessário:

```powershell
Copy-Item .env.example .env
```

O `.env` real deve ser criado e alterado manualmente. A aplicacao nao deve sobrescrever esse arquivo. Nunca versionar `COHERE_API_KEY` ou qualquer segredo; `.env` fica no `.gitignore`.

```env
APP_VERSION=0.5.6
DEFAULT_LANGUAGE=pt-BR

REQUIRE_API_KEY=false
LOCAL_API_KEY=dev-local-key-change-me
API_KEY_HEADER_NAME=X-API-Key
ALLOWED_CLIENT_ORIGINS=http://127.0.0.1:8020,http://localhost:8020
AUDIO_EMOTION_API_URL=http://127.0.0.1:8014

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
EMOTION_USE_LEARNING_EXAMPLES=true
EMOTION_MAX_LEARNING_EXAMPLES=3
EMOTION_CONFIDENCE_THRESHOLD=0.50
EMOTION_LEARNING_MIN_SIMILARITY=0.20
EMOTION_LEARNING_EXAMPLE_WEIGHT=0.25
EMOTION_TEXT_URGENCY_WEIGHT=0.14
EMOTION_TEXT_NEGATIVE_WEIGHT=0.12
EMOTION_HIGH_VOLUME_WEIGHT=0.12
EMOTION_LOW_VOLUME_WEIGHT=0.10
EMOTION_SILENCE_RATIO_WEIGHT=0.15
EMOTION_SPEECH_RATE_WEIGHT=0.10
EMOTION_PEAK_VOLUME_WEIGHT=0.12
EMOTION_COHERE_WEIGHT=0.65
EMOTION_FALLBACK_WEIGHT=0.35
EMOTION_HIGH_SILENCE_RATIO_THRESHOLD=0.35
EMOTION_LOW_WPM_THRESHOLD=85
EMOTION_HIGH_WPM_THRESHOLD=150
EMOTION_HIGH_PEAK_THRESHOLD=-8.0
EMOTION_LOW_VOLUME_THRESHOLD=-30.0
EXPORTS_DIR=exports
```

Para desativar Cohere e usar somente fallback local:

```env
USE_COHERE=false
```

Se `USE_COHERE=true`, `COHERE_API_KEY` estiver preenchida e a requisição usar `use_external_ai=true`, a API tenta chamar Cohere. Se a chamada falhar, a resposta continua funcionando com fallback local.

Para testar Cohere ativa:

```env
USE_COHERE=true
COHERE_ENABLED=true
COHERE_API_KEY=sua_chave_local
```

Para testar fallback local sem Cohere:

```env
USE_COHERE=false
```

Também é possível forçar fallback por requisição com `use_external_ai=false`, sem alterar o `.env`.

## Rodar a API

Porta padrão:

```bash
uvicorn app.main:app --reload
```

Porta alternativa, útil se a `8000` estiver bloqueada/reservada no Windows:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Se a `8011` tambem estiver presa por um processo antigo do Uvicorn, use outra porta livre, por exemplo:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8013
```

Abra a interface:

```txt
http://127.0.0.1:8013
```

Para descobrir e matar um processo antigo no Windows PowerShell:

```powershell
netstat -ano | findstr :8011
tasklist /FI "PID eq NUMERO_DO_PID"
Stop-Process -Id NUMERO_DO_PID -Force
```

## Diagnostico de Versao e Sistema

Use estes endpoints para confirmar que voce esta falando com a instancia correta:

```bash
curl http://127.0.0.1:8013/health
curl http://127.0.0.1:8013/v1/system/status
```

`/health` retorna status, app, versao, ambiente, versao do Python, engine de transcricao, modelo Whisper, provider emocional, Cohere habilitada, URL de banco resumida e diretorios principais.

`/v1/system/status` tambem retorna disponibilidade do FFmpeg, existencia do SQLite, quantidade de analises e quantidade de `learning_examples`. Nenhum endpoint retorna `COHERE_API_KEY`.

## Interface Web

A interface permite:

- testar `/health`;
- visualizar status do sistema;
- visualizar historico recente de analises;
- aprovar ou desaprovar `learning_examples`;
- preencher uma API Key local opcional para consumir endpoints protegidos;
- enviar arquivo `.mp3`, `.wav`, `.m4a`, `.webm` ou `.ogg`;
- gravar áudio pelo navegador usando `MediaRecorder`;
- escolher se deve tentar Cohere quando configurada;
- visualizar métricas acústicas reais;
- visualizar transcrição real;
- visualizar análise emocional interpretativa;
- visualizar fonte da emoção: `cohere` ou `local_heuristics`;
- visualizar evidências, observações e contexto recomendado;
- visualizar comparação Cohere vs fallback local;
- abrir a seção discreta `Debug da análise emocional`;
- enviar feedback para a análise.

## O Que Agora É Real

Métricas acústicas:

- duração;
- sample rate;
- volume médio;
- pico de volume;
- variação de volume;
- dynamic range;
- silêncio e pausas gerais;
- timeline de volume;
- eventos de pico;
- warning de qualidade.

Transcrição:

- texto completo;
- segmentos;
- palavras com timestamps quando o modelo retornar;
- engine/modelo usado;
- idioma detectado/configurado;
- word count;
- palavras por minuto;
- ritmo estimado;
- duração média por palavra quando houver timestamps.
- qualidade da transcrição, incluindo idioma usado, confiança média, uso de áudio otimizado e warnings.

Análise emocional:

- emoção primária;
- emoções secundárias;
- emoção implícita;
- tom emocional;
- intenção provável;
- urgência;
- calma;
- tensão;
- score de confiança;
- evidências usadas;
- transcrição comentada com `[emoção: ... | tom: ... | observação: ...]`.

A análise emocional é probabilística e interpretativa. Ela não deve ser tratada como certeza absoluta.

## Melhorando Qualidade da Transcrição

O pipeline mantém dois arquivos WAV processados:

- `*_16khz_mono.wav`: usado para métricas acústicas reais, sem filtros extras de inteligibilidade.
- `*_16khz_mono_transcription.wav`: usado apenas para transcrição, com filtros leves de FFmpeg (`highpass`, `lowpass` e `dynaudnorm`) para reduzir graves desnecessários e estabilizar volume.

Se a geração do áudio otimizado falhar, a API usa automaticamente o WAV padrão e informa isso em `transcription_quality.fallback_reason`.

O idioma `DEFAULT_LANGUAGE=pt-BR` é normalizado para `pt` antes de chamar o `faster-whisper`, que espera códigos de idioma curtos.

Parâmetros ajustáveis do `faster-whisper`:

```env
WHISPER_BEAM_SIZE=5
WHISPER_BEST_OF=5
WHISPER_TEMPERATURE=0
WHISPER_VAD_FILTER=true
WHISPER_CONDITION_ON_PREVIOUS_TEXT=false
```

Para melhorar a captura:

- fale perto do microfone, sem encostar nele;
- evite ruído, eco e música de fundo;
- evite gritar ou saturar o microfone, pois clipping perto de 0 dB prejudica a transcrição;
- prefira microfone externo quando possível;
- em gravações pelo navegador, confira os warnings de `transcription_quality` quando houver muito silêncio, áudio muito curto ou baixa confiança.

## Status no JSON

Com Cohere:

```json
{
  "status": {
    "acoustic_metrics_status": "real",
    "transcription_status": "real",
    "emotion_status": "real",
    "emotion_analysis_source": "cohere"
  }
}
```

## Debug e Comparação Emocional

A resposta inclui `emotion_debug` para transparência operacional:

```json
{
  "emotion_debug": {
    "provider_requested": "hybrid",
    "cohere_enabled": true,
    "cohere_attempted": true,
    "cohere_success": false,
    "fallback_used": true,
    "fallback_reason": "cohere_request_failed",
    "learning_examples_count": 1,
    "learning_examples_found": 1,
    "learning_examples_used_count": 1,
    "learning_min_similarity": 0.2,
    "learning_influence_applied": true,
    "learning_influence_summary": "1 exemplo aprovado parecido influenciou a analise.",
    "whether_learning_changed_result": false,
    "top_learning_examples": [
      {
        "id": 12,
        "similarity_score": 0.64,
        "corrected_primary_emotion": "inseguranca"
      }
    ],
    "heuristic_weights_snapshot": {},
    "heuristic_scores": {},
    "warnings": ["Falha ou indisponibilidade da Cohere; analise emocional gerada por fallback local."]
  }
}
```

A resposta também inclui `emotion_comparison`:

```json
{
  "emotion_comparison": {
    "local_before_learning": "preocupacao",
    "local_after_learning": "preocupacao",
    "local_primary_emotion": "preocupacao",
    "cohere_primary_emotion": "urgencia",
    "agreement_level": "partial",
    "learning_changed_local_result": false,
    "differences": ["Fallback local priorizou preocupacao; Cohere priorizou urgencia."]
  }
}
```

Divergências entre fallback local e Cohere são esperadas e úteis. Elas ajudam a entender onde calibrar heurísticas, prompts e exemplos locais futuramente. A análise continua sendo interpretativa/probabilística.

Com fallback local:

```json
{
  "status": {
    "acoustic_metrics_status": "real",
    "transcription_status": "real",
    "emotion_status": "fallback_local",
    "emotion_analysis_source": "local_heuristics"
  }
}
```

## Ainda Fora do Escopo

- fine-tuning;
- embeddings;
- RAG vetorial;
- WhisperX;
- openSMILE;
- SpeechBrain;
- Hugging Face Transformers;
- diarização;
- análise por sílaba;
- treinamento próprio;
- ajuste automático de pesos.

## Consumindo a Audio Emotion API com API Key

Esta camada simula o consumo futuro por outro app local. Ela e opcional e serve apenas para desenvolvimento; ainda nao e autenticacao comercial real, multiusuario, billing ou rate limit.

No `.env`, habilite:

```env
REQUIRE_API_KEY=true
LOCAL_API_KEY=dev-local-key-change-me
API_KEY_HEADER_NAME=X-API-Key
ALLOWED_CLIENT_ORIGINS=http://127.0.0.1:8020,http://localhost:8020
AUDIO_EMOTION_API_URL=http://127.0.0.1:8014
```

Rode a API em uma porta dedicada:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8014
```

Exemplo no Windows `cmd`/PowerShell com `curl.exe`:

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
    "emotion_status": "real ou fallback_local"
  },
  "transcription": {
    "text": "texto transcrito..."
  },
  "emotion_summary": {
    "primary_emotion": "calma",
    "confidence_score": 0.82
  },
  "recommended_context_for_ai_agent": "contexto recomendado..."
}
```

Quando `REQUIRE_API_KEY=true`, endpoints sensiveis exigem `X-API-Key`: analise de audio, consulta de analises, debug, contexto de aprendizado, feedback e gestao/listagem de `learning_examples`. Continuam publicos: `GET /`, `GET /health`, `GET /v1/system/status`, arquivos estaticos, Swagger/OpenAPI.

Para usar com um app cliente demo local em outra porta, mantenha a API em `http://127.0.0.1:8014` e inclua a origem do cliente em `ALLOWED_CLIENT_ORIGINS`, por exemplo `http://127.0.0.1:8020`.

O script de smoke para validar consumo externo:

```bash
python scripts/smoke_api_key_client.py
```

Ele usa `AUDIO_EMOTION_API_URL` quando definida, ou `http://127.0.0.1:8014` por padrao, envia a fixture `ptbr_01_calmo_normal.m4a` com `X-API-Key` e imprime `analysis_id`, status de transcricao, status emocional, emocao primaria e contexto recomendado. O script nunca imprime a chave.

## Enviar Áudio via curl

```bash
curl -X POST "http://127.0.0.1:8013/v1/analyze-audio" \
  -F "file=@samples/audio_teste.wav" \
  -F "language=pt-BR" \
  -F "use_external_ai=true" \
  -F "interpretation_style=interpretative"
```

Use `use_external_ai=false` para forçar fallback local na requisição.

## Feedback

```bash
curl -X POST "http://127.0.0.1:8013/v1/analyses/{analysis_id}/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": "negative",
    "is_correct": false,
    "corrected_primary_emotion": "ansiedade leve",
    "corrected_secondary_emotions": ["insegurança", "frustração leve"],
    "corrected_intention": "pedido de ajuda técnica",
    "corrected_tone": "calmo, mas inseguro",
    "correction_reason": "A análise exagerou urgência.",
    "approved_for_learning": true,
    "notes": "O tom era mais de dúvida e preocupação."
  }'
```

O feedback continua associado ao `analysis_id` e pode criar `learning_example` local para uso futuro em prompts da Cohere ou fallback evoluído.

## Aprendizado Local Simples

A aplicacao nao treina a Cohere e nao faz fine-tuning. O aprendizado atual e memoria local em SQLite:

- feedback humano pode virar `learning_example`;
- somente exemplos aprovados para reutilizacao entram automaticamente nas analises futuras;
- o ranking combina overlap de palavras importantes, proximidade de `silence_ratio`, `words_per_minute`, `avg_volume_db`, `peak_volume_db`, recencia e qualidade da correcao;
- o fallback local usa exemplos parecidos para reforcar ou ajustar scores heuristicos;
- a Cohere recebe os melhores exemplos parecidos no prompt, mas eles orientam a analise sem forcar a resposta;
- embeddings, RAG vetorial e ajuste automatico de pesos ainda nao existem.

Para listar exemplos salvos:

```bash
curl "http://127.0.0.1:8013/v1/learning/examples"
curl "http://127.0.0.1:8013/v1/learning/examples?approved_only=true&limit=20"
curl "http://127.0.0.1:8013/v1/learning/examples?corrected_emotion=inseguranca"
```

Para desativar um exemplo ruim sem apagar o historico:

```bash
curl -X PATCH "http://127.0.0.1:8013/v1/learning/examples/{example_id}" \
  -H "Content-Type: application/json" \
  -d '{"approved_for_reuse": false, "user_notes": "Removido do aprendizado local."}'
```

Para ver quais exemplos seriam usados em uma analise:

```bash
curl "http://127.0.0.1:8013/v1/analyses/{analysis_id}/learning-context"
```

`learning_influence_summary` explica se exemplos parecidos influenciaram a decisao. `whether_learning_changed_result` indica se o resultado local mudou depois de aplicar o historico.

## Onde os Dados São Salvos

- Original recebido: `AUDIO_STORAGE_DIR`.
- Áudio padronizado: `PROCESSED_AUDIO_DIR`.
- Métricas reais: tabela `audio_metrics`.
- Transcrição real: tabela `audio_analysis`.
- Palavras com timestamp: tabela `word_metrics`, quando disponíveis.
- Analise emocional: campos `emotion_status`, `emotion_analysis_source`, `emotion_analysis_model`, `emotion_summary_json`, `primary_emotion`, `secondary_emotions_json`, `confidence_score`, `learning_examples_used_json`, `warnings_json`, `emotion_debug_json`, `emotion_comparison_json`, `learning_influence_summary` e `learning_adjustments_json` em `audio_analysis`.
- Feedback: tabela `emotion_feedback`.
- Exemplos locais: tabela `learning_examples`, incluindo previsao original, emocoes/tom originais, correcao do usuario, tom corrigido, motivo da correcao, observacoes, trecho de transcricao, snapshot acustico e snapshot de ritmo.
- Exportacoes locais: `exports/learning_dataset.jsonl`.

`data/`, `storage/`, `exports/`, `.env`, `.venv` e arquivos reais de audio em `tests/fixtures/audio/*` ficam fora do Git. Mantenha apenas `tests/fixtures/audio/README.md` versionado.

## Exportar Dataset Local

Exportar todos os exemplos:

```bash
python scripts/export_learning_dataset.py
```

Exportar apenas exemplos aprovados:

```bash
python scripts/export_learning_dataset.py --approved-only
```

O arquivo padrao e `exports/learning_dataset.jsonl`, com uma linha JSON por exemplo contendo trecho de transcricao, snapshots acusticos, ritmo de fala, previsao original, correcao do usuario e status de aprovacao.

## Limpar Dados Locais

Ver o que seria removido sem apagar nada:

```bash
python scripts/cleanup_local_data.py --dry-run
```

Apagar o SQLite local configurado em `DATABASE_URL`:

```bash
python scripts/cleanup_local_data.py --yes
```

O script nao apaga `.env`, `.venv`, fixtures em `tests/fixtures/audio` nem arquivos de `storage`.

## Reset do Banco Local

Como o schema mudou na Rodada 5, a aplicação tenta adicionar colunas novas automaticamente em SQLite. Se o banco local antigo apresentar erro de schema:

1. Pare o servidor.
2. Apague `data/audio_emotion.db` ou `audio_emotion.db`, conforme seu `.env`.
3. Rode a aplicação novamente.

Alternativa segura:

```bash
python scripts/cleanup_local_data.py --dry-run
python scripts/cleanup_local_data.py --yes
```

## Testes

```bash
pytest
pytest -m real_audio
```

Os testes automatizados não baixam modelo do `faster-whisper`; o serviço de transcrição é mockado durante `pytest`.

## Validação com Áudios Reais de Referência

Fixtures disponíveis:

- `tests/fixtures/audio/ptbr_01_calmo_normal.m4a`
- `tests/fixtures/audio/ptbr_02_urgente_enfatico.m4a`
- `tests/fixtures/audio/ptbr_03_baixo_pausado.m4a`

Documentação:

```txt
tests/fixtures/audio/README.md
```

Esses arquivos devem ser adicionados localmente e nao sao versionados por padrao, pois podem conter voz real. Se eles nao existirem, `pytest -m real_audio` pula os testes correspondentes de forma controlada.

Validar as três fixtures com pipeline real e transcrição real local, sem depender de servidor externo:

```bash
python scripts/validate_audio_fixtures.py
```

Validar as três fixtures forçando fallback local sem alterar o `.env`:

```bash
python scripts/validate_audio_fixtures.py --no-cohere
```

Quando `REQUIRE_API_KEY=true`, os scripts internos leem `LOCAL_API_KEY` do `.env` e enviam o header configurado em `API_KEY_HEADER_NAME`, sem imprimir a chave no terminal.

Validar consumo HTTP externo com API Key:

```bash
python scripts/smoke_api_key_client.py
```

O script imprime metricas acusticas, WPM, status da transcricao, fonte da emocao, emocao primaria, urgencia, calma, confianca, fallback local, resultado da Cohere quando houver, nivel de concordancia, exemplos encontrados/usados, influencia do aprendizado, top exemplos e trecho da transcricao comentada. Os textos esperados sao aproximados.

## Teste Manual Recomendado

1. Rode `uvicorn app.main:app --reload --host 127.0.0.1 --port 8013`.
2. Abra `http://127.0.0.1:8013`.
3. Confira `Status do sistema` e a versao da API.
4. Envie `tests/fixtures/audio/ptbr_01_calmo_normal.m4a`.
5. Confira transcrição real, métricas reais, emoção interpretativa, comparação e debug.
6. Envie feedback e confira o `learning_example`.
7. Repita com `ptbr_02_urgente_enfatico.m4a`.
8. Repita com `ptbr_03_baixo_pausado.m4a`.
9. Exporte o dataset com `python scripts/export_learning_dataset.py --approved-only`.
10. Grave um áudio curto pelo navegador para validar captura local.

## Roadmap

1. Rodada futura: embeddings ou busca semantica local.
2. Rodada futura: calibragem assistida de pesos com base no historico.
3. Exportacoes, autenticacao e API publica futura.
