# PROJECT_CONTEXT.md — Audio Emotion API

> Documento de constituição do projeto para orientar o desenvolvimento inicial pelo Codex.
>
> Este arquivo deve ser colocado na raiz do repositório e tratado como a principal fonte de verdade do projeto.

---

## 1. Visão geral do projeto

O projeto consiste no desenvolvimento de uma API local-first para análise emocional de áudio.

A aplicação deve receber um áudio gravado ou arquivo de áudio, como MP3, WAV ou M4A, processar esse arquivo, transcrever seu conteúdo, analisar características acústicas da fala e retornar uma transcrição enriquecida com comentários emocionais, observações de tom, ritmo, intenção e comportamento vocal.

O objetivo principal é transformar um áudio em uma saída textual rica o suficiente para que outro agente de IA, que normalmente só receberia uma transcrição simples, consiga entender melhor a emoção, a intenção e o estado provável do interlocutor.

A primeira versão será focada em português brasileiro, áudio com apenas uma voz e execução local no computador do desenvolvedor. A arquitetura, porém, deve ser preparada para futuramente aceitar múltiplos idiomas, API pública, autenticação por chave de API e uso como serviço SaaS.

---

## 2. Nome interno do projeto

Nome sugerido:

```txt
Audio Emotion API
```

Nome técnico do repositório:

```txt
audio-emotion-api
```

---

## 3. Objetivo do MVP

O MVP deve permitir que o usuário envie um áudio para uma API local e receba como resposta:

1. A transcrição completa do áudio.
2. A transcrição comentada com observações emocionais entre colchetes.
3. Palavras ou trechos com maior ênfase.
4. Velocidade média da fala.
5. Tempo de fala por palavra.
6. Pausas entre palavras e frases.
7. Volume médio do áudio.
8. Variação de volume ao longo do áudio.
9. Indícios de calma, tensão, ansiedade, irritação, entusiasmo, insegurança ou outras emoções prováveis.
10. Um resumo breve da emoção percebida.
11. Um contexto recomendado para outro agente de IA responder melhor ao usuário.
12. Um identificador da análise salva no banco local.
13. Um mecanismo para o usuário avaliar/corrigir a análise e ajudar o app a melhorar com o tempo.

---

## 4. Filosofia do produto

O sistema não deve afirmar que detecta emoção com certeza absoluta.

A análise emocional deve ser tratada como uma inferência probabilística baseada em múltiplos sinais:

- conteúdo textual da fala;
- velocidade da fala;
- pausas;
- volume;
- variação de volume;
- ênfase em palavras;
- estrutura da frase;
- contexto semântico;
- histórico de feedbacks anteriores.

Toda emoção inferida deve ter um grau de confiança. O sistema deve diferenciar claramente:

- dados objetivos medidos no áudio;
- interpretação textual feita por IA;
- interpretação acústica feita por heurísticas/modelos;
- conclusão final combinada.

---

## 5. Escopo da V1

### 5.1. Incluído na V1

A primeira versão deve conter:

- API em FastAPI.
- Execução local.
- Upload de áudio por endpoint HTTP.
- Aceite inicial dos formatos `.mp3`, `.wav` e `.m4a`.
- Validação de arquivo.
- Conversão/padronização do áudio quando necessário.
- Processamento de áudios de até 10 minutos.
- Suporte inicial a um único interlocutor por áudio.
- Foco em português brasileiro.
- Transcrição automática.
- Extração de métricas acústicas básicas.
- Cálculo de palavras com maior ênfase.
- Cálculo de pausas e velocidade de fala.
- Geração de transcrição comentada.
- Geração de resumo emocional.
- Integração opcional com Cohere via chave no `.env`.
- Persistência local em SQLite.
- Salvamento das análises para consulta futura.
- Endpoint de feedback.
- Estrutura preparada para aprendizado incremental por histórico.
- Testes automatizados básicos.
- Documentação dos endpoints.

### 5.2. Fora da V1

Não implementar na primeira rodada:

- Interface visual web.
- SaaS público.
- Sistema completo de cobrança.
- Dashboard.
- Processamento assíncrono complexo.
- Diarização de múltiplos falantes.
- Análise perfeita por sílaba.
- Fine-tuning real de modelo externo.
- Treinamento de rede neural própria do zero.
- Deploy em nuvem.
- Login de usuários.
- Gateway de pagamento.

---

## 6. Escopo futuro

Fases futuras podem incluir:

- Suporte a áudios maiores que 10 minutos.
- Processamento assíncrono com fila.
- Endpoint de criação de jobs.
- Webhook de conclusão.
- Autenticação por chave de API.
- Site para oferecer o serviço.
- Dashboard de análises.
- Múltiplos usuários.
- Múltiplos idiomas.
- Diarização de falantes.
- Análise por sílaba/fonema.
- Sistema de avaliação humana mais completo.
- Dataset próprio para treinamento.
- Ajuste automático de pesos emocionais.
- Exportação dos resultados em JSON, TXT, Markdown e CSV.
- SDK em Python/JavaScript.

---

## 7. Stack técnica recomendada

### 7.1. Linguagem principal

```txt
Python 3.11+
```

### 7.2. API

```txt
FastAPI
Uvicorn
Pydantic
python-multipart
```

### 7.3. Áudio

```txt
FFmpeg
librosa
soundfile
pydub
numpy
```

### 7.4. Transcrição

Para o MVP, usar uma das alternativas abaixo, preferencialmente começando pela opção mais simples de instalar e rodar localmente:

```txt
faster-whisper
```

Opção futura para melhor alinhamento palavra por palavra:

```txt
WhisperX
```

### 7.5. Inteligência externa

```txt
Cohere API
```

A Cohere será usada para análise contextual, geração da transcrição comentada e interpretação emocional textual quando a chave `COHERE_API_KEY` estiver configurada.

A aplicação deve funcionar em modo degradado sem Cohere, retornando uma análise local simplificada.

### 7.6. Banco de dados

```txt
SQLite
SQLModel ou SQLAlchemy
```

Preferência para `SQLModel`, pois combina bem com FastAPI e Pydantic.

### 7.7. Testes

```txt
pytest
httpx
```

### 7.8. Qualidade de código

```txt
ruff
black
mypy opcional
```

---

## 8. Arquitetura geral

Fluxo principal:

```txt
Arquivo de áudio recebido
↓
Validação de tipo, tamanho e duração
↓
Salvamento temporário/local
↓
Conversão para formato padrão
↓
Extração de metadados do áudio
↓
Transcrição
↓
Alinhamento temporal por palavra
↓
Extração de métricas acústicas
↓
Cálculo de velocidade, pausas e ênfase
↓
Análise contextual via Cohere, se disponível
↓
Combinação das análises locais + IA externa
↓
Geração da transcrição comentada
↓
Geração do resumo emocional
↓
Persistência no SQLite
↓
Retorno JSON para o consumidor da API
```

---

## 9. Estrutura de pastas esperada

O Codex deve criar ou respeitar a seguinte estrutura:

```txt
audio-emotion-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_audio.py
│   │   ├── routes_feedback.py
│   │   ├── routes_health.py
│   │   └── schemas.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── errors.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── session.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audio_loader.py
│   │   ├── audio_preprocessor.py
│   │   ├── transcription_service.py
│   │   ├── alignment_service.py
│   │   ├── prosody_service.py
│   │   ├── emphasis_service.py
│   │   ├── emotion_service.py
│   │   ├── cohere_service.py
│   │   ├── learning_service.py
│   │   ├── feedback_service.py
│   │   └── response_builder.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── transcription_models.py
│   │   ├── prosody_models.py
│   │   ├── emotion_models.py
│   │   └── feedback_models.py
│   │
│   ├── prompts/
│   │   ├── emotion_analysis_prompt.md
│   │   └── annotated_transcript_prompt.md
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py
│       ├── audio_utils.py
│       ├── text_utils.py
│       └── hash_utils.py
│
├── tests/
│   ├── test_api_health.py
│   ├── test_audio_upload.py
│   ├── test_response_schema.py
│   ├── test_feedback.py
│   └── test_prosody_metrics.py
│
├── docs/
│   ├── PROJECT_CONTEXT.md
│   ├── API_CONTRACT.md
│   ├── DEVELOPMENT_PLAN.md
│   └── EMOTION_SCHEMA.md
│
├── samples/
│   ├── README.md
│   └── .gitkeep
│
├── storage/
│   ├── audio/
│   │   └── .gitkeep
│   ├── processed/
│   │   └── .gitkeep
│   └── exports/
│       └── .gitkeep
│
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── pyproject.toml
└── PROJECT_CONTEXT.md
```

---

## 10. Variáveis de ambiente

Criar `.env.example` com:

```env
APP_NAME=Audio Emotion API
APP_ENV=local
APP_DEBUG=true

DATABASE_URL=sqlite:///./audio_emotion.db

COHERE_API_KEY=
COHERE_MODEL=command-r-plus
COHERE_ENABLED=true

MAX_AUDIO_DURATION_SECONDS=600
MAX_AUDIO_FILE_SIZE_MB=100
DEFAULT_LANGUAGE=pt-BR

STORAGE_DIR=storage
AUDIO_STORAGE_DIR=storage/audio
PROCESSED_AUDIO_DIR=storage/processed
```

Observação: o projeto deve funcionar mesmo se `COHERE_API_KEY` estiver vazia. Nesse caso, usar apenas análise local simplificada.

---

## 11. Endpoints da V1

### 11.1. Health check

```http
GET /health
```

Resposta esperada:

```json
{
  "status": "ok",
  "app": "Audio Emotion API",
  "version": "0.1.0"
}
```

---

### 11.2. Analisar áudio

```http
POST /v1/analyze-audio
```

Tipo:

```txt
multipart/form-data
```

Campos:

```txt
file: arquivo de áudio
language: opcional, padrão pt-BR
use_external_ai: opcional, boolean, padrão true
interpretation_style: opcional, padrão interpretative
```

Valores permitidos para `interpretation_style`:

```txt
conservative
balanced
interpretative
```

Para este projeto, o padrão deve ser `interpretative`, conforme preferência do dono do projeto.

---

### 11.3. Buscar análise por ID

```http
GET /v1/analyses/{analysis_id}
```

Retorna uma análise já processada e salva no banco.

---

### 11.4. Listar análises

```http
GET /v1/analyses
```

Parâmetros futuros:

```txt
limit
offset
language
primary_emotion
created_after
created_before
```

Na V1, pode retornar as últimas análises em ordem decrescente.

---

### 11.5. Enviar feedback

```http
POST /v1/analyses/{analysis_id}/feedback
```

Payload:

```json
{
  "rating": "negative",
  "is_correct": false,
  "corrected_primary_emotion": "ansiedade leve",
  "corrected_secondary_emotions": ["insegurança", "frustração leve"],
  "corrected_intention": "pedido de ajuda técnica",
  "notes": "A análise exagerou a irritação. O tom era mais de dúvida e preocupação."
}
```

Valores aceitos para `rating`:

```txt
positive
neutral
negative
```

---

### 11.6. Listar exemplos de aprendizado

```http
GET /v1/learning/examples
```

Retorna exemplos aprovados/corrigidos que podem ser usados como memória para melhorar análises futuras.

---

## 12. Contrato de resposta principal

O endpoint `POST /v1/analyze-audio` deve retornar um JSON semelhante a este:

```json
{
  "analysis_id": "uuid",
  "metadata": {
    "file_name": "audio.mp3",
    "file_hash": "sha256_hash",
    "language": "pt-BR",
    "duration_seconds": 134.52,
    "processing_version": "0.1.0",
    "external_ai_used": true,
    "created_at": "2026-07-03T00:00:00Z"
  },
  "transcription": {
    "text": "Eu queria entender por que isso não está funcionando...",
    "segments": [
      {
        "id": 1,
        "start": 0.0,
        "end": 5.4,
        "text": "Eu queria entender por que isso não está funcionando."
      }
    ],
    "words": [
      {
        "word": "Eu",
        "start": 0.0,
        "end": 0.18,
        "duration_ms": 180,
        "pause_before_ms": 0,
        "pause_after_ms": 40,
        "confidence": 0.91
      }
    ]
  },
  "annotated_transcription": {
    "text": "Eu queria entender [emoção: dúvida | tom: calmo, mas inseguro | observação: início com baixa intensidade] por que isso não está funcionando [emoção: frustração leve | tom: mais firme | observação: aumento de ênfase em 'não funcionando']...",
    "annotation_style": "inline_brackets",
    "language": "pt-BR"
  },
  "prosody_summary": {
    "speech_rate_wpm": 138,
    "pace": "normal",
    "avg_volume_db": -21.4,
    "max_volume_db": -8.2,
    "volume_variance": 0.37,
    "pause_ratio": 0.18,
    "emphasis_words": [
      {
        "word": "não",
        "start": 3.21,
        "end": 3.45,
        "emphasis_score": 0.82,
        "reason": "aumento relativo de volume e posição semântica negativa"
      }
    ],
    "calmness_score": 0.68,
    "tension_score": 0.42
  },
  "emotion_summary": {
    "primary_emotion": "preocupação",
    "secondary_emotions": ["dúvida", "frustração leve"],
    "implicit_emotion": "insegurança diante de uma dificuldade",
    "interlocutor_calmness": "moderadamente calmo",
    "urgency_level": "médio",
    "intention": "pedir explicação ou suporte",
    "confidence_score": 0.78,
    "interpretation_style": "interpretative"
  },
  "important_observations": [
    "A fala tem ritmo controlado, mas apresenta aumento de intensidade em palavras negativas.",
    "O interlocutor parece buscar ajuda, não confronto.",
    "Há sinais de preocupação leve e tentativa de explicar o problema."
  ],
  "recommended_context_for_ai_agent": "O usuário demonstra preocupação leve e busca ajuda. Responder com calma, objetividade e tom acolhedor.",
  "quality_warnings": [],
  "feedback": {
    "feedback_url": "/v1/analyses/{analysis_id}/feedback",
    "message": "Envie feedback positivo ou negativo para melhorar análises futuras."
  }
}
```

---

## 13. Formato da transcrição comentada

A transcrição comentada deve ser uma das principais entregas do sistema.

Ela deve manter o texto original do áudio e inserir comentários emocionais entre colchetes em pontos relevantes.

Formato obrigatório:

```txt
[emoção: ... | tom: ... | observação: ...]
```

Exemplo:

```txt
Eu queria entender [emoção: dúvida | tom: calmo, mas inseguro | observação: fala começa controlada, com baixa intensidade] por que isso não está funcionando [emoção: frustração leve | tom: mais firme | observação: aumento de volume na palavra "não"] porque eu já tentei algumas vezes [emoção: cansaço | tom: desacelerado | observação: pausa antes da frase indica possível desgaste] e não consegui resolver [emoção: preocupação | tom: queda de energia vocal | observação: final com menor volume].
```

Regras:

1. Não inserir comentário em todas as palavras.
2. Inserir comentários apenas em pontos relevantes.
3. Não destruir a legibilidade da transcrição.
4. Evitar excesso de interpretação sem base.
5. Priorizar trechos com mudança de volume, pausa, emoção textual ou ênfase.
6. Usar português brasileiro.
7. Manter tom claro para outro agente de IA entender.

---

## 14. Métricas acústicas mínimas da V1

O sistema deve tentar calcular:

### 14.1. Métricas globais

- duração total do áudio;
- volume médio;
- volume máximo;
- variação de volume;
- quantidade de silêncio;
- proporção de silêncio;
- velocidade média da fala;
- palavras por minuto;
- número total de palavras;
- número de pausas relevantes.

### 14.2. Métricas por palavra

Quando timestamps por palavra estiverem disponíveis:

- palavra;
- início;
- fim;
- duração em milissegundos;
- pausa antes;
- pausa depois;
- volume aproximado no trecho da palavra;
- score de ênfase;
- confiança da transcrição.

### 14.3. Métricas interpretativas

- calma provável;
- tensão provável;
- hesitação;
- urgência;
- entusiasmo;
- irritação provável;
- insegurança provável.

---

## 15. Cálculo de ênfase

A ênfase não deve depender apenas do volume absoluto.

Ela deve considerar:

- volume relativo da palavra em comparação com a média do áudio;
- aumento repentino de volume;
- duração alongada da palavra;
- pausa antes da palavra;
- pausa depois da palavra;
- importância semântica da palavra;
- presença de negação;
- presença de termos emocionais;
- posição da palavra na frase.

Exemplo de heurística inicial:

```txt
emphasis_score =
  0.35 * normalized_word_volume
+ 0.20 * volume_delta_before_word
+ 0.15 * word_duration_relative
+ 0.10 * pause_before_score
+ 0.10 * pause_after_score
+ 0.10 * semantic_importance_score
```

O score deve ir de 0 a 1.

---

## 16. Emoções e estados suportados na V1

A V1 deve trabalhar com um conjunto inicial de emoções/estados:

```txt
calma
preocupação
ansiedade leve
ansiedade alta
frustração leve
frustração alta
irritação
tristeza
entusiasmo
confiança
insegurança
dúvida
urgência
cansaço
desânimo
neutralidade
```

Também deve detectar intenção provável:

```txt
pedido de ajuda
reclamação
explicação
relato pessoal
ordem/comando
pergunta
negociação
desabafo
solicitação técnica
feedback
objeção
```

---

## 17. Integração com Cohere

A Cohere será usada para interpretação contextual e geração de texto final.

### 17.1. Quando usar Cohere

Usar Cohere quando:

- `COHERE_ENABLED=true`;
- `COHERE_API_KEY` estiver configurada;
- o usuário não desativar `use_external_ai` na requisição;
- houver transcrição suficiente para análise.

### 17.2. Quando não usar Cohere

Não usar Cohere quando:

- não houver chave configurada;
- a transcrição estiver vazia;
- houver erro de rede/API;
- o limite de uso for atingido;
- `use_external_ai=false`.

Nesses casos, retornar análise local simplificada.

### 17.3. Estratégia para economizar chamadas

A Cohere não deve ser chamada para cada palavra.

Ela deve receber um pacote consolidado contendo:

- transcrição completa;
- segmentos;
- palavras enfatizadas;
- métricas acústicas globais;
- principais pausas;
- exemplos anteriores parecidos, se existirem;
- instruções para retornar JSON estruturado.

---

## 18. Prompt base para Cohere

Criar arquivo:

```txt
app/prompts/emotion_analysis_prompt.md
```

Conteúdo base:

```md
Você é um analisador de emoção, intenção e tom de fala para áudios em português brasileiro.

Você receberá:

1. Uma transcrição de áudio.
2. Métricas acústicas extraídas do áudio.
3. Palavras com possível ênfase.
4. Pausas e velocidade de fala.
5. Exemplos anteriores corrigidos pelo usuário, quando disponíveis.

Sua tarefa é gerar uma análise interpretativa, mas responsável, sobre o estado emocional provável do interlocutor.

Regras:

- Não declare emoção como certeza absoluta.
- Use linguagem clara e objetiva.
- Indique emoção primária, emoções secundárias e intenção provável.
- Gere uma transcrição comentada com observações entre colchetes.
- Os comentários devem seguir o formato:
  [emoção: ... | tom: ... | observação: ...]
- Não comente todas as palavras.
- Comente apenas pontos relevantes.
- Retorne somente JSON válido.
- Não invente dados acústicos que não foram fornecidos.
- Se a evidência for fraca, informe baixa confiança.
- A interpretação deve ser útil para outro agente de IA responder melhor ao usuário.

Formato de saída obrigatório:

{
  "annotated_transcription": "...",
  "emotion_summary": {
    "primary_emotion": "...",
    "secondary_emotions": ["..."],
    "implicit_emotion": "...",
    "interlocutor_calmness": "...",
    "urgency_level": "baixo|médio|alto",
    "intention": "...",
    "confidence_score": 0.0
  },
  "important_observations": ["..."],
  "recommended_context_for_ai_agent": "..."
}
```

---

## 19. Aprendizado incremental

O app deve melhorar com o tempo usando feedbacks do usuário.

Na V1, não será feito fine-tuning de modelo. O aprendizado será baseado em:

1. Persistência das análises.
2. Correções manuais do usuário.
3. Exemplos aprovados.
4. Comparação com casos anteriores.
5. Ajuste futuro de heurísticas/pesos.
6. Uso de exemplos similares no prompt enviado à Cohere.

### 19.1. Feedback positivo

Quando o usuário marcar uma análise como correta, o app deve salvar essa análise como exemplo confiável.

### 19.2. Feedback negativo

Quando o usuário marcar uma análise como errada, o app deve salvar:

- previsão original;
- emoção correta informada;
- intenção correta, se informada;
- observações do usuário;
- trecho problemático, se informado.

### 19.3. Uso em análises futuras

Antes de chamar a Cohere, o app pode buscar exemplos anteriores parecidos e incluir no prompt.

Exemplo conceitual:

```txt
Casos anteriores semelhantes corrigidos pelo usuário:

1. Texto: "eu não sei mais o que fazer..."
   Predição antiga: tristeza
   Correção: ansiedade leve com frustração

2. Texto: "já tentei várias vezes e não consigo resolver"
   Predição antiga: irritação
   Correção: preocupação e pedido de ajuda

Considere esses exemplos ao analisar o novo áudio.
```

---

## 20. Banco de dados

Usar SQLite na V1.

### 20.1. Tabela `audio_analysis`

Campos sugeridos:

```txt
id: UUID/string
file_name: string
file_hash: string
duration_seconds: float
language: string
transcription_text: text
annotated_transcription: text
final_summary_json: json/text
recommended_context_for_ai_agent: text
external_ai_used: bool
processing_version: string
created_at: datetime
```

### 20.2. Tabela `audio_metrics`

```txt
id: int
analysis_id: foreign key
avg_volume_db: float
max_volume_db: float
volume_variance: float
speech_rate_wpm: float
pause_ratio: float
calmness_score: float
tension_score: float
created_at: datetime
```

### 20.3. Tabela `word_metrics`

```txt
id: int
analysis_id: foreign key
word: string
start_time: float
end_time: float
duration_ms: int
pause_before_ms: int
pause_after_ms: int
volume_at_word: float
emphasis_score: float
confidence: float
comment: text nullable
```

### 20.4. Tabela `emotion_feedback`

```txt
id: int
analysis_id: foreign key
rating: string
is_correct: bool
corrected_primary_emotion: string nullable
corrected_secondary_emotions: json/text nullable
corrected_intention: string nullable
notes: text nullable
created_at: datetime
```

### 20.5. Tabela `learning_examples`

```txt
id: int
source_analysis_id: foreign key
text_excerpt: text
original_prediction: json/text
corrected_prediction: json/text
user_notes: text
approved_for_reuse: bool
created_at: datetime
```

---

## 21. Serviços internos

### 21.1. `audio_loader.py`

Responsável por:

- validar arquivo recebido;
- verificar extensão;
- verificar tamanho;
- salvar arquivo em diretório temporário/local;
- calcular hash do arquivo.

### 21.2. `audio_preprocessor.py`

Responsável por:

- converter áudio para WAV padronizado;
- normalizar sample rate;
- garantir canal mono quando necessário;
- preparar arquivo para transcrição e análise.

### 21.3. `transcription_service.py`

Responsável por:

- transcrever áudio;
- retornar texto completo;
- retornar segmentos;
- retornar palavras com timestamp quando possível.

Na primeira rodada, pode retornar mock se a dependência de transcrição ainda não estiver instalada.

### 21.4. `prosody_service.py`

Responsável por:

- calcular volume médio;
- calcular volume máximo;
- calcular variação de volume;
- calcular silêncio;
- calcular velocidade da fala;
- calcular pausas.

### 21.5. `emphasis_service.py`

Responsável por:

- calcular score de ênfase por palavra;
- detectar palavras destacadas;
- explicar motivo da ênfase.

### 21.6. `cohere_service.py`

Responsável por:

- montar prompt;
- chamar Cohere;
- validar retorno;
- tratar erros;
- retornar análise textual/emocional estruturada.

### 21.7. `emotion_service.py`

Responsável por:

- combinar análise local + Cohere;
- gerar emoção primária;
- gerar emoções secundárias;
- gerar score de confiança;
- gerar observações importantes.

### 21.8. `learning_service.py`

Responsável por:

- buscar exemplos anteriores;
- filtrar exemplos aprovados;
- preparar contexto histórico para a Cohere;
- futuramente calcular embeddings.

### 21.9. `feedback_service.py`

Responsável por:

- registrar feedback;
- transformar feedback em exemplo de aprendizado;
- marcar exemplos como aprovados ou não.

### 21.10. `response_builder.py`

Responsável por:

- montar o JSON final;
- garantir consistência de schema;
- incluir warnings;
- incluir URL de feedback.

---

## 22. Tratamento de erros

A API deve retornar erros claros.

### 22.1. Arquivo inválido

```json
{
  "detail": "Formato de áudio não suportado. Envie mp3, wav ou m4a."
}
```

### 22.2. Áudio muito longo

```json
{
  "detail": "Áudio excede o limite de 600 segundos da V1."
}
```

### 22.3. Falha na transcrição

```json
{
  "detail": "Não foi possível transcrever o áudio. Verifique a qualidade do arquivo."
}
```

### 22.4. Cohere indisponível

Não quebrar a análise inteira.

Retornar:

```json
{
  "quality_warnings": [
    "Análise externa via Cohere indisponível. Resultado gerado apenas com análise local simplificada."
  ]
}
```

---

## 23. Warnings de qualidade

A resposta deve incluir `quality_warnings` quando necessário:

```txt
áudio muito baixo
áudio com ruído
áudio com música de fundo
transcrição com baixa confiança
fala muito rápida
fala muito lenta
muitas pausas longas
volume muito instável
possível corte no áudio
arquivo muito comprimido
```

---

## 24. Segurança e privacidade

Na V1 local:

- os áudios podem ser salvos localmente para histórico e aprendizado;
- o usuário deve conseguir apagar arquivos futuramente;
- não enviar áudio bruto para Cohere na V1, apenas texto e métricas;
- salvar hash do arquivo para evitar duplicidade;
- não colocar chave da Cohere no código;
- usar `.env`;
- nunca commitar `.env`;
- não commitar arquivos de áudio reais;
- incluir `storage/audio/*` no `.gitignore`, mantendo apenas `.gitkeep`.

---

## 25. `.gitignore` esperado

Criar `.gitignore` com:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
.venv/
venv/
env/

# Env
.env
.env.local

# Database
*.db
*.sqlite
*.sqlite3

# Storage
storage/audio/*
storage/processed/*
storage/exports/*
!storage/audio/.gitkeep
!storage/processed/.gitkeep
!storage/exports/.gitkeep

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Test/cache
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
```

---

## 26. Requisitos de programação

O Codex deve seguir estas práticas:

1. Código modular.
2. Serviços separados por responsabilidade.
3. Não concentrar lógica pesada em `main.py`.
4. Usar Pydantic/SQLModel para schemas.
5. Tipar funções sempre que possível.
6. Criar testes básicos desde o início.
7. Tratar erros de forma explícita.
8. Não inventar dependências desnecessárias.
9. Não implementar interface visual na V1.
10. Não expor secrets.
11. Manter comentários apenas onde ajudam a entender regra de negócio.
12. Documentar endpoints no README.
13. Separar camada de API, serviços e banco.
14. Criar mocks temporários quando dependências pesadas ainda não estiverem integradas.
15. Priorizar uma primeira versão funcional e testável.

---

## 27. Ordem de implementação para o Codex

### Rodada 1 — Bootstrap obrigatório

O Codex deve começar por:

1. Criar estrutura de pastas.
2. Criar `requirements.txt` ou `pyproject.toml`.
3. Criar FastAPI em `app/main.py`.
4. Criar endpoint `GET /health`.
5. Criar endpoint `POST /v1/analyze-audio`.
6. Criar schemas Pydantic de request/response.
7. Criar validação inicial de arquivo.
8. Criar salvamento local em `storage/audio`.
9. Criar banco SQLite.
10. Criar modelos/tabelas principais.
11. Criar response mockado no contrato final.
12. Criar endpoint de feedback.
13. Criar testes básicos.
14. Criar README com instruções de execução.
15. Criar `.env.example`.

Importante: na primeira rodada, a resposta mockada já deve seguir o contrato final para facilitar evolução posterior.

### Rodada 2 — Métricas reais de áudio

Implementar:

1. Leitura real do áudio.
2. Duração.
3. Conversão básica para WAV, se necessário.
4. Volume médio.
5. Volume máximo.
6. Variação de volume.
7. Detecção simples de silêncio.
8. Warnings de qualidade.

### Rodada 3 — Transcrição

Implementar:

1. Serviço de transcrição local.
2. Texto completo.
3. Segmentos.
4. Palavras com timestamps, se possível.
5. Duração por palavra.
6. Pausas entre palavras.

### Rodada 4 — Emoção e Cohere

Implementar:

1. Serviço Cohere.
2. Prompt estruturado.
3. Análise contextual.
4. Transcrição comentada.
5. Resumo emocional.
6. Fallback local quando Cohere falhar.

### Rodada 5 — Feedback e aprendizado

Implementar:

1. Registro de feedback.
2. Criação de exemplos de aprendizado.
3. Busca de exemplos anteriores.
4. Inclusão de exemplos no prompt.
5. Estrutura para ajustes futuros de pesos.

---

## 28. Critérios de aceite da primeira versão funcional

A primeira versão será considerada funcional quando:

1. A API iniciar localmente com `uvicorn`.
2. `GET /health` retornar status `ok`.
3. `POST /v1/analyze-audio` aceitar um arquivo de áudio.
4. O áudio for validado e salvo localmente.
5. Uma análise for salva no SQLite.
6. A resposta seguir o contrato JSON planejado.
7. O endpoint de feedback funcionar.
8. Testes básicos passarem.
9. O projeto tiver README explicando como rodar.
10. `.env.example` estiver criado.

---

## 29. Comandos esperados para ambiente local

### 29.1. Criar ambiente virtual

```bash
python -m venv .venv
```

### 29.2. Ativar ambiente no Windows PowerShell

```bash
.venv\Scripts\Activate.ps1
```

### 29.3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 29.4. Rodar API

```bash
uvicorn app.main:app --reload
```

### 29.5. Rodar testes

```bash
pytest
```

---

## 30. README inicial esperado

O README deve conter:

1. Nome do projeto.
2. Descrição curta.
3. Objetivo.
4. Stack.
5. Como instalar.
6. Como configurar `.env`.
7. Como rodar.
8. Como testar `/health`.
9. Como enviar um áudio via `curl`.
10. Exemplo de resposta.
11. Como enviar feedback.
12. Roadmap.

Exemplo de `curl`:

```bash
curl -X POST "http://localhost:8000/v1/analyze-audio" \
  -F "file=@samples/audio_teste.mp3" \
  -F "language=pt-BR" \
  -F "use_external_ai=true" \
  -F "interpretation_style=interpretative"
```

---

## 31. Observações importantes para o Codex

O Codex deve entender que este projeto não é apenas uma transcrição de áudio.

O diferencial é a criação de uma transcrição emocionalmente enriquecida, capaz de ajudar outros agentes de IA a entenderem o estado emocional e a intenção do usuário.

A saída mais importante do sistema é:

```txt
transcrição completa + comentários emocionais inline + resumo emocional + contexto recomendado para outra IA
```

Não transformar o projeto em um front-end. Não focar em tela visual. A prioridade é a API, o contrato JSON, a arquitetura e o pipeline de análise.

---

## 32. Primeira tarefa exata para o Codex

Quando o Codex iniciar, ele deve executar a seguinte missão:

```txt
Leia integralmente o arquivo PROJECT_CONTEXT.md.

Depois, implemente a Rodada 1 do projeto Audio Emotion API:

- criar estrutura de pastas;
- configurar FastAPI;
- criar endpoint /health;
- criar endpoint /v1/analyze-audio;
- validar upload de áudio;
- salvar arquivo localmente;
- criar SQLite com tabelas iniciais;
- criar schemas Pydantic;
- retornar resposta mockada no contrato final;
- criar endpoint de feedback;
- criar testes básicos;
- criar README;
- criar .env.example;
- garantir que pytest passe.

Não implemente ainda transcrição real, Cohere real ou análise acústica avançada. Deixe serviços preparados com mocks, docstrings e TODOs claros para a próxima rodada.
```

---

## 33. Princípio final

Este projeto deve ser construído como uma base sólida, evolutiva e testável.

A V1 não precisa ser perfeita. Ela precisa estabelecer corretamente:

- arquitetura;
- contrato da API;
- persistência;
- feedback;
- formato de saída;
- preparação para análise emocional real.

Depois disso, cada camada de inteligência será adicionada progressivamente.

