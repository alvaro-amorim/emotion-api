const state = {
  selectedFile: null,
  recorder: null,
  recordedChunks: [],
  recordedBlob: null,
  recordingStartedAt: null,
  timerId: null,
  analysisId: null,
  feedbackRating: "positive",
  feedbackIsCorrect: true,
};

const elements = {
  statusDot: document.getElementById("statusDot"),
  statusText: document.getElementById("statusText"),
  healthButton: document.getElementById("healthButton"),
  refreshSystemStatusButton: document.getElementById("refreshSystemStatusButton"),
  systemVersion: document.getElementById("systemVersion"),
  systemHealth: document.getElementById("systemHealth"),
  systemTranscription: document.getElementById("systemTranscription"),
  systemWhisper: document.getElementById("systemWhisper"),
  systemCohere: document.getElementById("systemCohere"),
  systemAnalysesCount: document.getElementById("systemAnalysesCount"),
  systemLearningCount: document.getElementById("systemLearningCount"),
  systemFfmpeg: document.getElementById("systemFfmpeg"),
  versionWarning: document.getElementById("versionWarning"),
  refreshAnalysesButton: document.getElementById("refreshAnalysesButton"),
  recentAnalysesList: document.getElementById("recentAnalysesList"),
  refreshLearningExamplesButton: document.getElementById("refreshLearningExamplesButton"),
  learningExamplesList: document.getElementById("learningExamplesList"),
  audioFile: document.getElementById("audioFile"),
  useExternalAi: document.getElementById("useExternalAi"),
  selectedFileName: document.getElementById("selectedFileName"),
  analyzeFileButton: document.getElementById("analyzeFileButton"),
  recordingSupport: document.getElementById("recordingSupport"),
  startRecordingButton: document.getElementById("startRecordingButton"),
  stopRecordingButton: document.getElementById("stopRecordingButton"),
  recordingTimer: document.getElementById("recordingTimer"),
  recordedAudio: document.getElementById("recordedAudio"),
  analyzeRecordingButton: document.getElementById("analyzeRecordingButton"),
  messageArea: document.getElementById("messageArea"),
  resultSection: document.getElementById("resultSection"),
  analysisIdText: document.getElementById("analysisIdText"),
  processingStatusText: document.getElementById("processingStatusText"),
  metricDuration: document.getElementById("metricDuration"),
  metricSampleRate: document.getElementById("metricSampleRate"),
  metricAvgVolume: document.getElementById("metricAvgVolume"),
  metricPeakVolume: document.getElementById("metricPeakVolume"),
  metricVariance: document.getElementById("metricVariance"),
  metricDynamicRange: document.getElementById("metricDynamicRange"),
  metricSilenceCount: document.getElementById("metricSilenceCount"),
  metricTotalSilence: document.getElementById("metricTotalSilence"),
  metricLongestSilence: document.getElementById("metricLongestSilence"),
  metricSilenceRatio: document.getElementById("metricSilenceRatio"),
  metricSpeechDuration: document.getElementById("metricSpeechDuration"),
  metricPeakCount: document.getElementById("metricPeakCount"),
  audioQualityWarning: document.getElementById("audioQualityWarning"),
  peakEvents: document.getElementById("peakEvents"),
  transcriptionStatusText: document.getElementById("transcriptionStatusText"),
  transcriptionText: document.getElementById("transcriptionText"),
  transcriptionEngine: document.getElementById("transcriptionEngine"),
  transcriptionModel: document.getElementById("transcriptionModel"),
  transcriptionLanguage: document.getElementById("transcriptionLanguage"),
  wordCount: document.getElementById("wordCount"),
  wordsPerMinute: document.getElementById("wordsPerMinute"),
  speechRateLabel: document.getElementById("speechRateLabel"),
  averageWordDuration: document.getElementById("averageWordDuration"),
  transcriptionSegments: document.getElementById("transcriptionSegments"),
  transcriptionWords: document.getElementById("transcriptionWords"),
  annotatedText: document.getElementById("annotatedText"),
  emotionSource: document.getElementById("emotionSource"),
  emotionModel: document.getElementById("emotionModel"),
  primaryEmotion: document.getElementById("primaryEmotion"),
  secondaryEmotions: document.getElementById("secondaryEmotions"),
  implicitEmotion: document.getElementById("implicitEmotion"),
  emotionalTone: document.getElementById("emotionalTone"),
  emotionIntention: document.getElementById("emotionIntention"),
  calmness: document.getElementById("calmness"),
  urgency: document.getElementById("urgency"),
  tension: document.getElementById("tension"),
  confidence: document.getElementById("confidence"),
  emotionEvidence: document.getElementById("emotionEvidence"),
  learningExamplesUsed: document.getElementById("learningExamplesUsed"),
  debugProvider: document.getElementById("debugProvider"),
  debugCohereEnabled: document.getElementById("debugCohereEnabled"),
  debugCohereAttempted: document.getElementById("debugCohereAttempted"),
  debugCohereSuccess: document.getElementById("debugCohereSuccess"),
  debugFallbackUsed: document.getElementById("debugFallbackUsed"),
  debugFallbackReason: document.getElementById("debugFallbackReason"),
  debugLearningExamplesCount: document.getElementById("debugLearningExamplesCount"),
  debugLearningExamplesFound: document.getElementById("debugLearningExamplesFound"),
  debugLearningMinSimilarity: document.getElementById("debugLearningMinSimilarity"),
  debugLearningApplied: document.getElementById("debugLearningApplied"),
  debugLearningChanged: document.getElementById("debugLearningChanged"),
  debugLearningSummary: document.getElementById("debugLearningSummary"),
  debugTopLearningExamples: document.getElementById("debugTopLearningExamples"),
  debugLearningAdjustments: document.getElementById("debugLearningAdjustments"),
  debugDecisionFactors: document.getElementById("debugDecisionFactors"),
  debugHeuristicSnapshot: document.getElementById("debugHeuristicSnapshot"),
  comparisonLocalPrimary: document.getElementById("comparisonLocalPrimary"),
  comparisonCoherePrimary: document.getElementById("comparisonCoherePrimary"),
  comparisonAgreement: document.getElementById("comparisonAgreement"),
  comparisonDifferences: document.getElementById("comparisonDifferences"),
  debugWarnings: document.getElementById("debugWarnings"),
  qualityWarnings: document.getElementById("qualityWarnings"),
  importantObservations: document.getElementById("importantObservations"),
  recommendedContext: document.getElementById("recommendedContext"),
  fullJson: document.getElementById("fullJson"),
  feedbackSection: document.getElementById("feedbackSection"),
  ratingButtons: document.querySelectorAll(".rating-button"),
  correctedEmotion: document.getElementById("correctedEmotion"),
  correctedTone: document.getElementById("correctedTone"),
  correctionReason: document.getElementById("correctionReason"),
  approvedForLearning: document.getElementById("approvedForLearning"),
  feedbackNotes: document.getElementById("feedbackNotes"),
  sendFeedbackButton: document.getElementById("sendFeedbackButton"),
  feedbackMessage: document.getElementById("feedbackMessage"),
};

function setMessage(text, type = "") {
  elements.messageArea.textContent = text;
  elements.messageArea.className = `message ${type}`.trim();
}

function setStatus(kind, text) {
  elements.statusDot.className = `status-dot status-${kind}`;
  elements.statusText.textContent = text;
}

function setLoading(isLoading, text = "Processando áudio") {
  elements.analyzeFileButton.disabled = isLoading || !state.selectedFile;
  elements.analyzeRecordingButton.disabled = isLoading || !state.recordedBlob;
  elements.startRecordingButton.disabled =
    isLoading || !navigator.mediaDevices || !window.MediaRecorder;
  elements.sendFeedbackButton.disabled = isLoading || !state.analysisId;
  if (isLoading) {
    setMessage(text, "");
  }
}

function formatTimer(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function startTimer() {
  state.recordingStartedAt = Date.now();
  elements.recordingTimer.textContent = "00:00";
  state.timerId = window.setInterval(() => {
    elements.recordingTimer.textContent = formatTimer(Date.now() - state.recordingStartedAt);
  }, 250);
}

function stopTimer() {
  if (state.timerId) {
    window.clearInterval(state.timerId);
    state.timerId = null;
  }
}

async function checkHealth() {
  try {
    setStatus("idle", "Verificando API");
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    setStatus("ok", `${payload.app} ${payload.version} online`);
  } catch (error) {
    setStatus("error", `Falha no /health: ${error.message}`);
  }
}

async function loadSystemStatus() {
  try {
    const response = await fetch("/v1/system/status");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    elements.systemVersion.textContent = payload.version || "-";
    elements.systemHealth.textContent = payload.status || "-";
    elements.systemTranscription.textContent = payload.transcription_engine || "-";
    elements.systemWhisper.textContent = payload.whisper_model_size || "-";
    elements.systemCohere.textContent = payload.cohere_enabled
      ? "Cohere ativa"
      : payload.cohere_configured
        ? "Fallback local por configuracao"
        : "Fallback local";
    elements.systemAnalysesCount.textContent =
      typeof payload.analyses_count === "number" ? String(payload.analyses_count) : "-";
    elements.systemLearningCount.textContent =
      typeof payload.learning_examples_count === "number"
        ? String(payload.learning_examples_count)
        : "-";
    elements.systemFfmpeg.textContent = payload.ffmpeg_available ? "disponivel" : "indisponivel";

    if (!String(payload.version || "").startsWith("0.5.")) {
      elements.versionWarning.textContent =
        "A resposta nao parece ser da versao 0.5.x. Verifique se ha outro uvicorn antigo rodando em outra porta.";
      elements.versionWarning.classList.remove("hidden");
    } else {
      elements.versionWarning.textContent = "";
      elements.versionWarning.classList.add("hidden");
    }
  } catch (error) {
    elements.systemHealth.textContent = `erro: ${error.message}`;
  }
}

async function loadRecentAnalyses() {
  try {
    const response = await fetch("/v1/analyses?limit=8");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    const records = (payload.analyses || []).map((analysis) => {
      const item = document.createElement("article");
      item.className = "record-card";

      const metadata = analysis.metadata || {};
      const emotion = analysis.emotion_summary || {};
      const status = analysis.status || {};
      const transcription = analysis.transcription || {};

      const title = document.createElement("h3");
      title.textContent = metadata.file_name || analysis.analysis_id;
      item.appendChild(title);

      const body = document.createElement("p");
      body.textContent = [
        `id: ${analysis.analysis_id}`,
        `data: ${formatDate(metadata.created_at)}`,
        `duracao: ${formatSeconds(metadata.duration_seconds)}`,
        `emocao: ${emotion.primary_emotion || "-"}`,
        `fonte: ${status.emotion_analysis_source || "-"}`,
        `confianca: ${formatPercent(emotion.confidence_score)}`,
      ].join(" | ");
      item.appendChild(body);

      const preview = document.createElement("p");
      preview.className = "record-preview";
      preview.textContent = shorten(transcription.text || "Sem transcricao.", 180);
      item.appendChild(preview);

      const links = document.createElement("div");
      links.className = "record-actions";
      links.appendChild(recordLink(`/v1/analyses/${analysis.analysis_id}`, "detalhes"));
      links.appendChild(recordLink(`/v1/analyses/${analysis.analysis_id}/debug`, "debug"));
      item.appendChild(links);
      return item;
    });

    if (records.length === 0) {
      elements.recentAnalysesList.textContent = "Nenhuma analise salva ainda.";
      return;
    }
    elements.recentAnalysesList.replaceChildren(...records);
  } catch (error) {
    elements.recentAnalysesList.textContent = `Erro ao carregar historico: ${error.message}`;
  }
}

async function loadLearningExamples() {
  try {
    const response = await fetch("/v1/learning/examples?limit=10");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    const records = (payload.examples || []).map((example) => renderLearningExampleRecord(example));
    if (records.length === 0) {
      elements.learningExamplesList.textContent = "Nenhum learning example salvo ainda.";
      return;
    }
    elements.learningExamplesList.replaceChildren(...records);
  } catch (error) {
    elements.learningExamplesList.textContent = `Erro ao carregar exemplos: ${error.message}`;
  }
}

function renderLearningExampleRecord(example) {
  const item = document.createElement("article");
  item.className = "record-card";

  const title = document.createElement("h3");
  title.textContent = `#${example.id} | ${example.corrected_primary_emotion || "sem correcao"}`;
  item.appendChild(title);

  const body = document.createElement("p");
  body.textContent = [
    `analysis_id: ${example.source_analysis_id}`,
    `aprovado: ${yesNo(example.approved_for_reuse)}`,
    `tom: ${example.corrected_tone || "-"}`,
    `origem: ${example.emotion_analysis_source || "-"}`,
  ].join(" | ");
  item.appendChild(body);

  const preview = document.createElement("p");
  preview.className = "record-preview";
  preview.textContent = shorten(example.text_excerpt || example.transcription_excerpt || "-", 220);
  item.appendChild(preview);

  const actions = document.createElement("div");
  actions.className = "record-actions";
  const approveButton = document.createElement("button");
  approveButton.type = "button";
  approveButton.textContent = "Aprovar";
  approveButton.disabled = example.approved_for_reuse === true;
  approveButton.addEventListener("click", () => updateLearningExampleApproval(example.id, true));
  const disableButton = document.createElement("button");
  disableButton.type = "button";
  disableButton.textContent = "Desaprovar";
  disableButton.disabled = example.approved_for_reuse === false;
  disableButton.addEventListener("click", () => updateLearningExampleApproval(example.id, false));
  actions.append(approveButton, disableButton);
  item.appendChild(actions);
  return item;
}

async function updateLearningExampleApproval(exampleId, approved) {
  try {
    const response = await fetch(`/v1/learning/examples/${exampleId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved_for_reuse: approved }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    setMessage(`Learning example #${exampleId} atualizado.`, "success");
    await Promise.all([loadLearningExamples(), loadSystemStatus()]);
  } catch (error) {
    setMessage(`Erro ao atualizar exemplo: ${error.message}`, "error");
  }
}

function recordLink(href, text) {
  const link = document.createElement("a");
  link.href = href;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = text;
  return link;
}

function shorten(text, maxLength) {
  if (!text || text.length <= maxLength) {
    return text || "";
  }
  return `${text.slice(0, maxLength - 3)}...`;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString("pt-BR");
}

async function analyzeAudio(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", "pt-BR");
  formData.append("use_external_ai", elements.useExternalAi.checked ? "true" : "false");
  formData.append("interpretation_style", "interpretative");

  setLoading(true);
  elements.feedbackMessage.textContent = "";

  try {
    const response = await fetch("/v1/analyze-audio", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }

    renderAnalysis(payload);
    await Promise.all([loadSystemStatus(), loadRecentAnalyses()]);
    setMessage("Análise concluída.", "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    setLoading(false);
  }
}

function renderAnalysis(payload) {
  const emotion = payload.emotion_summary || {};
  const metrics = payload.acoustic_metrics || {};
  const status = payload.status || {};
  state.analysisId = payload.analysis_id;

  elements.resultSection.classList.remove("hidden");
  elements.feedbackSection.classList.remove("hidden");
  elements.analysisIdText.textContent = `analysis_id: ${payload.analysis_id}`;
  renderAcousticMetrics(metrics, status);
  renderTranscription(payload.transcription || {}, status);
  elements.annotatedText.textContent = payload.annotated_transcription?.text || "";
  elements.emotionSource.textContent = status.emotion_analysis_source || emotion.analysis_source || "-";
  elements.emotionModel.textContent = emotion.analysis_model || "-";
  elements.primaryEmotion.textContent = emotion.primary_emotion || "-";
  elements.secondaryEmotions.textContent = (emotion.secondary_emotions || []).join(", ") || "-";
  elements.implicitEmotion.textContent = emotion.implicit_emotion || "-";
  elements.emotionalTone.textContent = emotion.emotional_tone || "-";
  elements.emotionIntention.textContent = emotion.intention || "-";
  elements.calmness.textContent = emotion.interlocutor_calmness || "-";
  elements.urgency.textContent = emotion.urgency_level || "-";
  elements.tension.textContent =
    typeof emotion.tension_score === "number" ? `${Math.round(emotion.tension_score * 100)}%` : "-";
  elements.confidence.textContent =
    typeof emotion.confidence_score === "number"
      ? `${Math.round(emotion.confidence_score * 100)}%`
      : "-";
  elements.recommendedContext.textContent = payload.recommended_context_for_ai_agent || "-";
  elements.fullJson.textContent = JSON.stringify(payload, null, 2);

  elements.importantObservations.replaceChildren(
    ...(payload.important_observations || []).map((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      return li;
    }),
  );
  renderEmotionEvidence(payload.emotion_evidence || []);
  renderLearningExamples(payload.learning_examples_used || []);
  renderEmotionDebug(payload.emotion_debug || {}, payload.emotion_comparison || {});
  renderQualityWarnings(payload.quality_warnings || []);
}

function replaceList(element, items, emptyText) {
  const listItems = items.map((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    return li;
  });
  if (listItems.length === 0) {
    const li = document.createElement("li");
    li.textContent = emptyText;
    listItems.push(li);
  }
  element.replaceChildren(...listItems);
}

function renderEmotionEvidence(evidence) {
  replaceList(
    elements.emotionEvidence,
    evidence.map(
      (item) =>
        `${item.type || "-"} | ${item.signal || "-"}: ${item.value ?? "-"} | ${item.impact || "-"}`,
    ),
    "Nenhuma evidência específica retornada.",
  );
}

function renderLearningExamples(examples) {
  replaceList(
    elements.learningExamplesUsed,
    examples.map(
      (item) =>
        `#${item.id} | similaridade ${Math.round((item.similarity_score || 0) * 100)}% | texto ${Math.round(
          (item.text_similarity || 0) * 100,
        )}% | metricas ${Math.round((item.metric_similarity || 0) * 100)}% | ${
          item.correction_summary || item.text_excerpt || "-"
        }`,
    ),
    "Nenhum exemplo local reutilizado nesta análise.",
  );
}

function renderQualityWarnings(warnings) {
  replaceList(elements.qualityWarnings, warnings, "Nenhum aviso adicional.");
}

function yesNo(value) {
  if (typeof value !== "boolean") {
    return "-";
  }
  return value ? "sim" : "não";
}

function renderEmotionDebug(debug, comparison) {
  elements.debugProvider.textContent = debug.provider_requested || "-";
  elements.debugCohereEnabled.textContent = yesNo(debug.cohere_enabled);
  elements.debugCohereAttempted.textContent = yesNo(debug.cohere_attempted);
  elements.debugCohereSuccess.textContent = yesNo(debug.cohere_success);
  elements.debugFallbackUsed.textContent = yesNo(debug.fallback_used);
  elements.debugFallbackReason.textContent = debug.fallback_reason || "-";
  elements.debugLearningExamplesCount.textContent =
    typeof debug.learning_examples_count === "number" ? String(debug.learning_examples_count) : "-";
  elements.debugLearningExamplesFound.textContent =
    typeof debug.learning_examples_found === "number" ? String(debug.learning_examples_found) : "-";
  elements.debugLearningMinSimilarity.textContent =
    typeof debug.learning_min_similarity === "number"
      ? `${Math.round(debug.learning_min_similarity * 100)}%`
      : "-";
  elements.debugLearningApplied.textContent = yesNo(debug.learning_influence_applied);
  elements.debugLearningChanged.textContent = yesNo(debug.whether_learning_changed_result);
  elements.debugLearningSummary.textContent =
    debug.learning_influence_summary || "Nenhuma influencia de aprendizado aplicada.";
  elements.comparisonLocalPrimary.textContent = comparison.local_primary_emotion || "-";
  elements.comparisonCoherePrimary.textContent = comparison.cohere_primary_emotion || "-";
  elements.comparisonAgreement.textContent = comparison.agreement_level || "-";
  replaceList(
    elements.debugTopLearningExamples,
    (debug.top_learning_examples || []).map(
      (item) =>
        `#${item.id} | similaridade ${Math.round((item.similarity_score || 0) * 100)}% | ${
          item.corrected_primary_emotion || "-"
        } | ${item.reason_used || "-"}`,
    ),
    "Nenhum exemplo parecido acima do limite configurado.",
  );
  replaceList(
    elements.debugLearningAdjustments,
    debug.learning_adjustments || [],
    "Nenhum ajuste por aprendizado.",
  );
  replaceList(
    elements.debugDecisionFactors,
    debug.final_decision_factors || [],
    "Nenhum fator final detalhado.",
  );
  elements.debugHeuristicSnapshot.textContent = JSON.stringify(
    {
      weights: debug.heuristic_weights_snapshot || {},
      scores: debug.heuristic_scores || {},
    },
    null,
    2,
  );
  replaceList(
    elements.comparisonDifferences,
    comparison.differences || [],
    "Nenhuma divergência relevante reportada.",
  );
  replaceList(elements.debugWarnings, debug.warnings || [], "Nenhum warning de debug.");
}

function renderTranscription(transcription, status) {
  elements.transcriptionStatusText.textContent = [
    `status: ${status.transcription_status || "-"}`,
    `emoção: ${status.emotion_status || "-"}`,
    `fonte: ${status.emotion_analysis_source || "-"}`,
  ].join(" | ");
  elements.transcriptionText.textContent = transcription.text || "Sem texto transcrito.";
  elements.transcriptionEngine.textContent = transcription.transcription_engine || "-";
  elements.transcriptionModel.textContent = transcription.transcription_model || "-";
  elements.transcriptionLanguage.textContent = transcription.detected_language || "-";
  elements.wordCount.textContent =
    typeof transcription.word_count === "number" ? String(transcription.word_count) : "-";
  elements.wordsPerMinute.textContent =
    typeof transcription.words_per_minute === "number"
      ? transcription.words_per_minute.toFixed(2)
      : "-";
  elements.speechRateLabel.textContent = transcription.estimated_speech_rate_label || "-";
  elements.averageWordDuration.textContent =
    typeof transcription.average_word_duration_ms === "number"
      ? `${transcription.average_word_duration_ms.toFixed(0)} ms`
      : "-";

  const segmentItems = (transcription.segments || []).map((segment) => {
    const li = document.createElement("li");
    li.textContent = `${formatSeconds(segment.start)} - ${formatSeconds(segment.end)} | ${segment.text}`;
    return li;
  });
  if (segmentItems.length === 0) {
    const li = document.createElement("li");
    li.textContent = "Nenhum segmento retornado.";
    segmentItems.push(li);
  }
  elements.transcriptionSegments.replaceChildren(...segmentItems);

  const wordItems = (transcription.words || []).slice(0, 80).map((word) => {
    const li = document.createElement("li");
    li.textContent = `${word.word} (${formatSeconds(word.start)} - ${formatSeconds(word.end)})`;
    return li;
  });
  if ((transcription.words || []).length > 80) {
    const li = document.createElement("li");
    li.textContent = `... mais ${(transcription.words || []).length - 80} palavras`;
    wordItems.push(li);
  }
  if (wordItems.length === 0) {
    const li = document.createElement("li");
    li.textContent = "Palavras com timestamps não disponíveis para este áudio.";
    wordItems.push(li);
  }
  elements.transcriptionWords.replaceChildren(...wordItems);
}

function formatSeconds(value) {
  return typeof value === "number" ? `${value.toFixed(2)}s` : "-";
}

function formatDb(value) {
  return typeof value === "number" ? `${value.toFixed(2)} dB` : "-";
}

function formatPercent(value) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "-";
}

function renderAcousticMetrics(metrics, status) {
  elements.processingStatusText.textContent = [
    `acústica: ${status.acoustic_metrics_status || "-"}`,
    `transcrição: ${status.transcription_status || "-"}`,
    `emoção: ${status.emotion_status || "-"}`,
    `fonte: ${status.emotion_analysis_source || "-"}`,
  ].join(" | ");
  elements.metricDuration.textContent = formatSeconds(metrics.duration_seconds);
  elements.metricSampleRate.textContent =
    typeof metrics.sample_rate === "number" ? `${metrics.sample_rate} Hz` : "-";
  elements.metricAvgVolume.textContent = formatDb(metrics.avg_volume_db);
  elements.metricPeakVolume.textContent = formatDb(metrics.peak_volume_db);
  elements.metricVariance.textContent =
    typeof metrics.volume_variance === "number" ? metrics.volume_variance.toFixed(3) : "-";
  elements.metricDynamicRange.textContent = formatDb(metrics.dynamic_range_db);
  elements.metricSilenceCount.textContent =
    typeof metrics.silence_count === "number" ? String(metrics.silence_count) : "-";
  elements.metricTotalSilence.textContent = formatSeconds(metrics.total_silence_duration_seconds);
  elements.metricLongestSilence.textContent = formatSeconds(metrics.longest_silence_seconds);
  elements.metricSilenceRatio.textContent = formatPercent(metrics.silence_ratio);
  elements.metricSpeechDuration.textContent = formatSeconds(
    metrics.estimated_speech_duration_seconds,
  );
  elements.metricPeakCount.textContent =
    typeof metrics.peak_count === "number" ? String(metrics.peak_count) : "-";

  if (metrics.audio_quality_warning) {
    elements.audioQualityWarning.textContent = metrics.audio_quality_warning;
    elements.audioQualityWarning.classList.remove("hidden");
  } else {
    elements.audioQualityWarning.textContent = "";
    elements.audioQualityWarning.classList.add("hidden");
  }

  const peakItems = (metrics.peak_events || []).map((event) => {
    const li = document.createElement("li");
    li.textContent = `${formatSeconds(event.time_seconds)} | ${formatDb(event.volume_db)} | ${event.intensity_label}`;
    return li;
  });
  if (peakItems.length === 0) {
    const li = document.createElement("li");
    li.textContent = "Nenhum pico relevante detectado.";
    peakItems.push(li);
  }
  elements.peakEvents.replaceChildren(...peakItems);
}

function selectFeedback(button) {
  elements.ratingButtons.forEach((item) => item.classList.remove("is-selected"));
  button.classList.add("is-selected");
  state.feedbackRating = button.dataset.rating;
  state.feedbackIsCorrect = button.dataset.correct === "true";
}

async function sendFeedback() {
  if (!state.analysisId) {
    elements.feedbackMessage.textContent = "Faça uma análise antes de enviar feedback.";
    return;
  }

  const correctedEmotion = elements.correctedEmotion.value.trim();
  const correctedTone = elements.correctedTone.value.trim();
  const correctionReason = elements.correctionReason.value.trim();
  const notes = elements.feedbackNotes.value.trim();
  const payload = {
    rating: state.feedbackRating,
    is_correct: state.feedbackIsCorrect,
    corrected_primary_emotion: correctedEmotion || null,
    corrected_secondary_emotions: null,
    corrected_intention: null,
    corrected_tone: correctedTone || null,
    correction_reason: correctionReason || null,
    approved_for_learning: elements.approvedForLearning.checked,
    notes: notes || null,
  };

  elements.sendFeedbackButton.disabled = true;
  elements.feedbackMessage.textContent = "Enviando feedback";

  try {
    const response = await fetch(`/v1/analyses/${state.analysisId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const responsePayload = await response.json();
    if (!response.ok) {
      throw new Error(responsePayload.detail || `HTTP ${response.status}`);
    }
    elements.feedbackMessage.textContent = responsePayload.message || "Feedback registrado.";
    await Promise.all([loadSystemStatus(), loadLearningExamples()]);
  } catch (error) {
    elements.feedbackMessage.textContent = error.message;
  } finally {
    elements.sendFeedbackButton.disabled = false;
  }
}

async function startRecording() {
  try {
    state.recordedChunks = [];
    state.recordedBlob = null;
    elements.recordedAudio.removeAttribute("src");
    elements.recordedAudio.classList.remove("has-audio");
    elements.analyzeRecordingButton.disabled = true;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    state.recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

    state.recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        state.recordedChunks.push(event.data);
      }
    });

    state.recorder.addEventListener("stop", () => {
      state.recordedBlob = new Blob(state.recordedChunks, {
        type: state.recorder.mimeType || "audio/webm",
      });
      const audioUrl = URL.createObjectURL(state.recordedBlob);
      elements.recordedAudio.src = audioUrl;
      elements.recordedAudio.classList.add("has-audio");
      elements.analyzeRecordingButton.disabled = false;
      stream.getTracks().forEach((track) => track.stop());
      stopTimer();
    });

    state.recorder.start();
    startTimer();
    elements.startRecordingButton.disabled = true;
    elements.stopRecordingButton.disabled = false;
    setMessage("Gravação em andamento.", "");
  } catch (error) {
    setMessage(`Não foi possível iniciar a gravação: ${error.message}`, "error");
  }
}

function stopRecording() {
  if (state.recorder && state.recorder.state !== "inactive") {
    state.recorder.stop();
    elements.startRecordingButton.disabled = false;
    elements.stopRecordingButton.disabled = true;
    setMessage("Gravação pronta para análise.", "success");
  }
}

function initializeRecordingSupport() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    elements.recordingSupport.textContent = "Gravação indisponível neste navegador";
    elements.startRecordingButton.disabled = true;
    return;
  }
  elements.recordingSupport.textContent = "MediaRecorder disponível";
}

elements.healthButton.addEventListener("click", checkHealth);
elements.refreshSystemStatusButton.addEventListener("click", loadSystemStatus);
elements.refreshAnalysesButton.addEventListener("click", loadRecentAnalyses);
elements.refreshLearningExamplesButton.addEventListener("click", loadLearningExamples);
elements.audioFile.addEventListener("change", (event) => {
  const [file] = event.target.files;
  state.selectedFile = file || null;
  elements.selectedFileName.textContent = file ? file.name : "Nenhum arquivo selecionado";
  elements.analyzeFileButton.disabled = !file;
});
elements.analyzeFileButton.addEventListener("click", () => {
  if (state.selectedFile) {
    analyzeAudio(state.selectedFile);
  }
});
elements.startRecordingButton.addEventListener("click", startRecording);
elements.stopRecordingButton.addEventListener("click", stopRecording);
elements.analyzeRecordingButton.addEventListener("click", () => {
  if (state.recordedBlob) {
    const file = new File([state.recordedBlob], "recorded-audio.webm", {
      type: state.recordedBlob.type || "audio/webm",
    });
    analyzeAudio(file);
  }
});
elements.ratingButtons.forEach((button) => {
  button.addEventListener("click", () => selectFeedback(button));
});
elements.sendFeedbackButton.addEventListener("click", sendFeedback);

selectFeedback(document.querySelector(".rating-button"));
initializeRecordingSupport();
checkHealth();
loadSystemStatus();
loadRecentAnalyses();
loadLearningExamples();
