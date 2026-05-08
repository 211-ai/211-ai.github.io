import { useEffect, useRef, useState } from "react";
import { Loader2, Mic, MicOff, PhoneOff, Volume2, VolumeX } from "lucide-react";
import type { AgentMessage } from "../../agent/types";
import type { ClientAudioProgress } from "../../lib/clientAudioReplyService";
import { clientAudioReplyService } from "../../lib/clientAudioReplyService";
import { Button } from "../ui";

type AudioSessionState = "ready" | "listening" | "thinking" | "speaking" | "unavailable";
type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

interface BrowserSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  abort: () => void;
  start: () => void;
  stop: () => void;
}

interface BrowserSpeechRecognitionEvent {
  resultIndex: number;
  results: ArrayLike<{
    isFinal: boolean;
    0?: {
      transcript?: string;
    };
  }>;
}

export function AgentAudioChatSurface({
  activeRouteLabel,
  messages,
  open,
  responding,
  onClose,
  onSend
}: {
  activeRouteLabel: string;
  messages: AgentMessage[];
  open: boolean;
  responding?: boolean;
  onClose: () => void;
  onSend: (message: string) => void;
}) {
  const [sessionState, setSessionState] = useState<AudioSessionState>("ready");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [modelProgress, setModelProgress] = useState<ClientAudioProgress | null>(null);
  const [muted, setMuted] = useState(false);
  const [statusDetail, setStatusDetail] = useState("");
  const finalTranscriptRef = useRef("");
  const audioProgressRequestIdRef = useRef(0);
  const lastSpokenAssistantIdRef = useRef<string | undefined>(getLastAssistantMessage(messages)?.id);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const openRef = useRef(open);

  useEffect(() => {
    if (open && !openRef.current) {
      lastSpokenAssistantIdRef.current = getLastAssistantMessage(messages)?.id;
      setSessionState("ready");
      setStatusDetail("");
    }
    if (!open && openRef.current) {
      audioProgressRequestIdRef.current += 1;
      cancelListening();
      stopPlayback();
      setInterimTranscript("");
      setModelProgress(null);
    }
    openRef.current = open;
  }, [messages, open]);

  useEffect(() => {
    if (!open) return;
    const requestId = ++audioProgressRequestIdRef.current;
    void clientAudioReplyService
      .warmUp({
        onProgress: (progress) => updateModelProgress(requestId, progress),
      })
      .then((result) => {
        if (audioProgressRequestIdRef.current !== requestId || !openRef.current) return;
        setModelProgress(null);
        setStatusDetail(result.kind === "local-ready" ? "Audio model ready." : "Browser speech output ready.");
      })
      .catch((error) => {
        if (audioProgressRequestIdRef.current !== requestId || !openRef.current) return;
        setModelProgress(null);
        setStatusDetail(error instanceof Error ? error.message : "Audio model warmup failed.");
      });
  }, [open]);

  useEffect(() => {
    if (!open || muted || responding) return;
    const assistantMessage = getLastAssistantMessage(messages);
    if (!assistantMessage || assistantMessage.id === lastSpokenAssistantIdRef.current) return;
    lastSpokenAssistantIdRef.current = assistantMessage.id;
    void speakAssistantMessage(assistantMessage);
  }, [messages, muted, open, responding]);

  useEffect(() => {
    if (responding && open) {
      setSessionState("thinking");
    } else if (sessionState === "thinking") {
      setSessionState("ready");
    }
  }, [open, responding, sessionState]);

  function startListening() {
    const Recognition = getSpeechRecognitionConstructor();
    if (!Recognition) {
      setSessionState("unavailable");
      setStatusDetail("Speech recognition is not available in this browser.");
      return;
    }
    stopPlayback();
    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = navigator.language || "en-US";
    finalTranscriptRef.current = "";
    setInterimTranscript("");
    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = result[0]?.transcript ?? "";
        if (result.isFinal) {
          finalTranscriptRef.current = `${finalTranscriptRef.current} ${text}`.trim();
        } else {
          interim = `${interim} ${text}`.trim();
        }
      }
      setInterimTranscript(interim || finalTranscriptRef.current);
    };
    recognition.onerror = (event) => {
      setSessionState("ready");
      setStatusDetail(formatSpeechRecognitionError(event.error));
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      const transcript = finalTranscriptRef.current.trim();
      setInterimTranscript("");
      if (transcript) {
        onSend(transcript);
        setSessionState("thinking");
        setStatusDetail("");
      } else {
        setSessionState("ready");
      }
    };
    recognitionRef.current = recognition;
    setSessionState("listening");
    setStatusDetail("");
    try {
      recognition.start();
    } catch (error) {
      recognitionRef.current = null;
      setSessionState("ready");
      setStatusDetail(error instanceof Error ? error.message : "Voice input could not start.");
    }
  }

  function stopListening() {
    const recognition = recognitionRef.current;
    if (!recognition) return;
    try {
      recognition.stop();
    } catch {
      recognition.abort();
      recognitionRef.current = null;
      setSessionState("ready");
    }
  }

  function cancelListening() {
    const recognition = recognitionRef.current;
    if (!recognition) return;
    recognition.onend = null;
    recognition.onerror = null;
    recognition.onresult = null;
    recognition.abort();
    recognitionRef.current = null;
  }

  async function speakAssistantMessage(message: AgentMessage) {
    if (!message.content.trim()) return;
    stopPlayback();
    setSessionState("speaking");
    setStatusDetail("");
    const requestId = ++audioProgressRequestIdRef.current;
    setModelProgress({
      phase: "queued",
      progress: 0,
      status: "Preparing audio reply.",
    });
    try {
      const result = await clientAudioReplyService.generateAudio(message.content, {
        onProgress: (progress) => updateModelProgress(requestId, progress),
      });
      if (audioProgressRequestIdRef.current !== requestId) return;
      setModelProgress(null);
      if (!openRef.current || muted) return;
      if (result.kind === "audio") {
        const audioUrl = URL.createObjectURL(result.audioBlob);
        audioUrlRef.current = audioUrl;
        const audio = new Audio(audioUrl);
        audioRef.current = audio;
        audio.onended = () => {
          revokeAudioUrl();
          setSessionState("ready");
        };
        audio.onerror = () => {
          revokeAudioUrl();
          setStatusDetail("Audio playback failed.");
          setSessionState("ready");
        };
        await audio.play();
        return;
      }
      setStatusDetail("Using browser speech output.");
      playBrowserSpeech(result.text);
    } catch (error) {
      if (audioProgressRequestIdRef.current === requestId) setModelProgress(null);
      setStatusDetail(error instanceof Error ? error.message : "Audio reply failed.");
      setSessionState("ready");
    }
  }

  function updateModelProgress(requestId: number, progress: ClientAudioProgress) {
    if (audioProgressRequestIdRef.current !== requestId || !openRef.current) return;
    setModelProgress(progress);
    setStatusDetail(progress.status);
  }

  function playBrowserSpeech(text: string) {
    if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
      setStatusDetail("Audio playback is not available in this browser.");
      setSessionState("ready");
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.96;
    utterance.pitch = 1;
    utterance.onend = () => setSessionState("ready");
    utterance.onerror = () => {
      setStatusDetail("Browser speech playback failed.");
      setSessionState("ready");
    };
    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }

  function stopPlayback() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (utteranceRef.current && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      utteranceRef.current = null;
    }
    revokeAudioUrl();
    if (sessionState === "speaking") {
      setSessionState("ready");
    }
  }

  function revokeAudioUrl() {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }

  function toggleMuted() {
    const nextMuted = !muted;
    setMuted(nextMuted);
    if (nextMuted) stopPlayback();
  }

  const visibleMessages = messages.slice(-8).filter((message) => message.role === "assistant" || message.role === "user");
  const isListening = sessionState === "listening";
  const isBusy = responding || sessionState === "thinking";
  const statusLabel = getAudioSessionStatusLabel(sessionState, responding);
  const progressValue = modelProgress ? clampProgress(modelProgress.progress) : 0;

  return (
    <div className="agent-audio-chat-content">
      <div className="agent-current-task agent-audio-session-status" role="status">
        <small>Voice chat</small>
        <span>{statusDetail || statusLabel}</span>
      </div>

      {modelProgress ? (
        <div
          aria-label="Audio model progress"
          aria-live="polite"
          className="agent-audio-model-progress"
          role="status"
        >
          <div className="agent-audio-model-progress-header">
            <strong>{formatProgressPhase(modelProgress.phase)}</strong>
            <span>{progressValue}%</span>
          </div>
          <progress max={100} value={progressValue}>
            {progressValue}%
          </progress>
          <small>{formatProgressDetail(modelProgress)}</small>
        </div>
      ) : null}

      <div className={`agent-audio-stage agent-audio-stage-${sessionState}`}>
        <button
          aria-label={isListening ? "Stop listening" : "Start voice chat"}
          className="agent-audio-orb"
          disabled={isBusy}
          onClick={isListening ? stopListening : startListening}
          type="button"
        >
          {isBusy ? (
            <Loader2 aria-hidden="true" className="agent-audio-spinner" size={38} />
          ) : isListening ? (
            <MicOff aria-hidden="true" size={38} />
          ) : (
            <Mic aria-hidden="true" size={38} />
          )}
        </button>
        <div className="agent-audio-wave" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
        <div className="agent-audio-route">
          <strong>Abby voice</strong>
          <small>{activeRouteLabel}</small>
        </div>
      </div>

      {interimTranscript ? (
        <div className="agent-audio-live-transcript" aria-live="polite">
          {interimTranscript}
        </div>
      ) : null}

      <div className="agent-audio-controls">
        <Button ariaLabel={muted ? "Unmute voice replies" : "Mute voice replies"} onClick={toggleMuted} variant="secondary">
          {muted ? <VolumeX aria-hidden="true" size={18} /> : <Volume2 aria-hidden="true" size={18} />}
          <span>{muted ? "Muted" : "Audio"}</span>
        </Button>
        <Button ariaLabel="Close voice chat" onClick={onClose} variant="secondary">
          <PhoneOff aria-hidden="true" size={18} />
          <span>End</span>
        </Button>
      </div>

      <div className="agent-audio-transcript" aria-label="Voice conversation transcript">
        {visibleMessages.map((message) => (
          <article className={`agent-audio-transcript-row agent-audio-transcript-${message.role}`} key={message.id}>
            <div className="agent-audio-transcript-meta">{message.role === "user" ? "You" : "Abby"}</div>
            <div className="agent-audio-transcript-bubble">
              <p>{message.content}</p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | undefined {
  const browserWindow = window as typeof window & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return browserWindow.SpeechRecognition ?? browserWindow.webkitSpeechRecognition;
}

function getLastAssistantMessage(messages: AgentMessage[]): AgentMessage | undefined {
  return [...messages].reverse().find((message) => message.role === "assistant" && message.status === "complete");
}

function getAudioSessionStatusLabel(sessionState: AudioSessionState, responding?: boolean): string {
  if (responding || sessionState === "thinking") return "Abby is working through your request.";
  if (sessionState === "listening") return "Listening.";
  if (sessionState === "speaking") return "Speaking.";
  if (sessionState === "unavailable") return "Speech recognition unavailable.";
  return "Ready.";
}

function formatSpeechRecognitionError(error?: string): string {
  if (error === "not-allowed") return "Microphone permission was blocked.";
  if (error === "no-speech") return "No speech was detected.";
  if (error === "audio-capture") return "Microphone input is unavailable.";
  return "Voice input stopped.";
}

function formatProgressPhase(phase: ClientAudioProgress["phase"]): string {
  if (phase === "loading-runtime") return "Loading runtime";
  if (phase === "downloading-model") return "Downloading model";
  if (phase === "warming-up") return "Warming up";
  if (phase === "generating") return "Generating audio";
  if (phase === "decoding") return "Decoding audio";
  if (phase === "ready") return "Audio ready";
  if (phase === "fallback") return "Fallback ready";
  return "Preparing audio";
}

function formatProgressDetail(progress: ClientAudioProgress): string {
  return progress.status;
}

function clampProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}
