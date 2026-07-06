# Audio Fixtures

Estes arquivos sao fixtures reais em portugues brasileiro para validar o pipeline local da Audio Emotion API.

Os textos esperados abaixo sao aproximados. A transcricao automatica pode variar conforme modelo do `faster-whisper`, ruido, volume, codecs e versao das dependencias.

## Arquivos

### `ptbr_01_calmo_normal.m4a`

Fala esperada aproximada:

> Ola, eu estou testando a analise de audio do aplicativo. Estou falando de forma calma, em um ritmo normal, sem pressa e sem aumentar muito o volume da voz. Quero verificar se o sistema consegue identificar uma fala estavel, tranquila e facil de entender.

Perfil acustico esperado:

- fala calma;
- ritmo normal;
- volume medio;
- pouca variacao brusca;
- poucas pausas longas.

### `ptbr_02_urgente_enfatico.m4a`

Fala esperada aproximada:

> Eu preciso resolver isso agora. Isso e muito importante e nao pode esperar. Ja tentei algumas vezes e o problema continua acontecendo. Preciso de uma resposta clara, rapida e objetiva para entender o que esta errado.

Perfil acustico esperado:

- fala mais urgente;
- volume mais alto;
- mais enfase;
- mais picos de volume;
- ritmo possivelmente mais rapido.

### `ptbr_03_baixo_pausado.m4a`

Fala esperada aproximada:

> Eu nao tenho certeza se consegui explicar direito. Talvez eu precise tentar de novo. As vezes eu fico um pouco inseguro quando o sistema nao entende o que eu quis dizer. Eu vou falar com calma para ver se agora funciona melhor.

Perfil acustico esperado:

- fala mais baixa;
- mais pausada;
- mais hesitante;
- volume medio menor;
- maior proporcao de silencio/pausa.

## Uso Pretendido

- Validar que `.m4a` continua sendo aceito e convertido via FFmpeg.
- Validar que as metricas acusticas reais sao calculadas para arquivos reais.
- Validar que a transcricao local real retorna texto para falas em portugues brasileiro.
- Comparar de forma manual e flexivel volume, picos e silencio entre perfis de fala diferentes.

Para validacao real com o modelo local, rode:

```bash
python scripts/validate_audio_fixtures.py
```

Os testes automatizados podem usar estas fixtures com transcricao mockada para manter `pytest` rapido e evitar download de modelo durante a suite normal.
