import { useEffect, useRef, useState } from "react";
import { Loader2, Mic, MicOff, PhoneOff, Volume2, VolumeX } from "lucide-react";
import type { AgentMessage } from "../../agent/types";
import type { ClientAudioProgress } from "../../lib/clientAudioReplyService";
import { clientAudioReplyService } from "../../lib/clientAudioReplyService";
import { Button } from "../ui";

type AudioSessionState = "ready" | "listening" | "thinking" | "speaking" | "unavailable";
type AgentAudioSurface = "drawer" | "sheet";
type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;
type BrowserAudioContextConstructor = new () => BrowserAudioContext;

const AUDIO_SURFACE_DESKTOP_QUERY = "(min-width: 760px)";
const AUDIO_OPENING_GREETING = "Hi, this is Abby voice. Press the microphone and start speaking.";
let lastOpeningGreetingAt = 0;

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

interface BrowserAudioContext {
  state?: AudioContextState;
  close: () => Promise<void>;
  createAnalyser: () => AnalyserNode;
  createMediaStreamSource: (stream: MediaStream) => MediaStreamAudioSourceNode;
  resume?: () => Promise<void>;
}

export function AgentAudioChatSurface({
  activeRouteLabel,
  messages,
  open,
  responding,
  surface = "drawer",
  onClose,
  onSend
}: {
  activeRouteLabel: string;
  messages: AgentMessage[];
  open: boolean;
  responding?: boolean;
  surface?: AgentAudioSurface;
  onClose: () => void;
  onSend: (message: string) => void;
}) {
  const [sessionState, setSessionState] = useState<AudioSessionState>("ready");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [micLevel, setMicLevel] = useState(0);
  const [modelProgress, setModelProgress] = useState<ClientAudioProgress | null>(null);
  const [muted, setMuted] = useState(false);
  const [statusDetail, setStatusDetail] = useState("");
  const [audioDiagnostic, setAudioDiagnostic] = useState("");
  const finalTranscriptRef = useRef("");
  const audioProgressRequestIdRef = useRef(0);
  const lastSpokenAssistantIdRef = useRef<string | undefined>(getLastAssistantMessage(messages)?.id);
  const micAnalyserRef = useRef<AnalyserNode | null>(null);
  const micAudioContextRef = useRef<BrowserAudioContext | null>(null);
  const micDataRef = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const micRafRef = useRef<number | null>(null);
  const micSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const mutedRef = useRef(muted);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const openRef = useRef(open);

  useEffect(() => {
    mutedRef.current = muted;
  }, [muted]);

  useEffect(() => {
    if (open && !openRef.current) {
      lastSpokenAssistantIdRef.current = getLastAssistantMessage(messages)?.id;
      setSessionState("ready");
      setStatusDetail("");
      setAudioDiagnostic("");
      setMicLevel(0);
    }
    if (!open && openRef.current) {
      audioProgressRequestIdRef.current += 1;
      cancelListening();
      stopPlayback();
      setInterimTranscript("");
      setModelProgress(null);
      setAudioDiagnostic("");
      setMicLevel(0);
    }
    openRef.current = open;
  }, [messages, open]);

  useEffect(() => {
    if (!open || !isAudioSurfaceActive(surface)) return;
    const requestId = ++audioProgressRequestIdRef.current;
    setAudioDiagnostic("");
    void clientAudioReplyService
      .warmUp({
        onProgress: (progress) => updateModelProgress(requestId, progress),
      })
      .then((result) => {
        if (audioProgressRequestIdRef.current !== requestId || !openRef.current) return;
        setModelProgress(null);
        if (result.kind === "local-ready") {
          setStatusDetail("Audio model ready.");
          setAudioDiagnostic("");
        } else {
          setStatusDetail("Browser speech output ready.");
          setAudioDiagnostic(result.fallbackReason);
        }
      })
      .catch((error) => {
        if (audioProgressRequestIdRef.current !== requestId || !openRef.current) return;
        const message = error instanceof Error ? error.message : "Audio model warmup failed.";
        setModelProgress(null);
        setStatusDetail(message);
        setAudioDiagnostic(message);
      });
  }, [open, surface]);

  useEffect(() => {
    if (!open || muted || !isAudioSurfaceActive(surface)) return;
    const timeout = window.setTimeout(() => {
      if (!openRef.current || mutedRef.current || !reserveOpeningGreeting()) return;
      setSessionState("speaking");
      setStatusDetail("Testing voice output.");
      playBrowserSpeech(AUDIO_OPENING_GREETING);
    }, 120);
    return () => window.clearTimeout(timeout);
  }, [muted, open, surface]);

  useEffect(() => {
    if (!open || muted || responding || !isAudioSurfaceActive(surface)) return;
    const assistantMessage = getLastAssistantMessage(messages);
    if (!assistantMessage || assistantMessage.id === lastSpokenAssistantIdRef.current) return;
    lastSpokenAssistantIdRef.current = assistantMessage.id;
    void speakAssistantMessage(assistantMessage);
  }, [messages, muted, open, responding, surface]);

  useEffect(() => {
    if (responding && open) {
      setSessionState("thinking");
    } else if (sessionState === "thinking") {
      setSessionState("ready");
    }
  }, [open, responding, sessionState]);

  async function startListening() {
    const Recognition = getSpeechRecognitionConstructor();
    if (!Recognition) {
      setSessionState("unavailable");
      setStatusDetail("Speech recognition is not available in this browser.");
      return;
    }
    stopPlayback();
    const microphoneReady = await startMicrophoneMeter();
    if (!microphoneReady || !openRef.current) return;
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
      stopMicrophoneMeter();
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      stopMicrophoneMeter();
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
      stopMicrophoneMeter();
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
      stopMicrophoneMeter();
      setSessionState("ready");
    }
  }

  function cancelListening() {
    const recognition = recognitionRef.current;
    if (!recognition) {
      stopMicrophoneMeter();
      return;
    }
    recognition.onend = null;
    recognition.onerror = null;
    recognition.onresult = null;
    recognition.abort();
    recognitionRef.current = null;
    stopMicrophoneMeter();
  }

  async function startMicrophoneMeter(): Promise<boolean> {
    stopMicrophoneMeter();
    if (!navigator.mediaDevices?.getUserMedia) {
      setSessionState("unavailable");
      setStatusDetail("Microphone input is not available in this browser.");
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      micStreamRef.current = stream;
      const AudioContextConstructor = getAudioContextConstructor();
      if (!AudioContextConstructor) {
        setStatusDetail("Microphone connected; input level meter is unavailable.");
        return true;
      }
      const audioContext = new AudioContextConstructor();
      if (audioContext.state === "suspended" && audioContext.resume) {
        await audioContext.resume();
      }
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.72;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      micAudioContextRef.current = audioContext;
      micAnalyserRef.current = analyser;
      micSourceRef.current = source;
      micDataRef.current = new Uint8Array(new ArrayBuffer(analyser.fftSize));
      setMicLevel(0);
      setStatusDetail("Microphone connected. Speak to check your input level.");
      monitorMicrophoneLevel();
      return true;
    } catch (error) {
      const message = formatMicrophoneError(error);
      setSessionState("unavailable");
      setStatusDetail(message);
      setAudioDiagnostic(message);
      stopMicrophoneMeter();
      return false;
    }
  }

  function monitorMicrophoneLevel() {
    const analyser = micAnalyserRef.current;
    const data = micDataRef.current;
    if (!analyser || !data) return;
    analyser.getByteTimeDomainData(data);
    let sumSquares = 0;
    for (let index = 0; index < data.length; index += 1) {
      const centered = (data[index] - 128) / 128;
      sumSquares += centered * centered;
    }
    const rms = Math.sqrt(sumSquares / data.length);
    setMicLevel(clampLevel(rms * 4.8));
    micRafRef.current = window.requestAnimationFrame(monitorMicrophoneLevel);
  }

  function stopMicrophoneMeter() {
    if (micRafRef.current !== null) {
      window.cancelAnimationFrame(micRafRef.current);
      micRafRef.current = null;
    }
    micSourceRef.current?.disconnect();
    micSourceRef.current = null;
    if (micAudioContextRef.current) {
      void micAudioContextRef.current.close().catch(() => undefined);
      micAudioContextRef.current = null;
    }
    micStreamRef.current?.getTracks().forEach((track) => track.stop());
    micStreamRef.current = null;
    micAnalyserRef.current = null;
    micDataRef.current = null;
    setMicLevel(0);
  }

  async function speakAssistantMessage(message: AgentMessage) {
    if (!message.content.trim()) return;
    stopPlayback();
    setSessionState("speaking");
    setStatusDetail("");
    setAudioDiagnostic("");
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
      setAudioDiagnostic(result.fallbackReason);
      playBrowserSpeech(result.text);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Audio reply failed.";
      if (audioProgressRequestIdRef.current === requestId) setModelProgress(null);
      setStatusDetail(message);
      setAudioDiagnostic(message);
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
  const micLevelPercent = Math.round(micLevel * 100);
  const waveHeights = getWaveHeights(isListening ? micLevel : 0);

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

      {audioDiagnostic ? (
        <div aria-label="Audio diagnostic" className="agent-audio-diagnostic" role="alert">
          {audioDiagnostic}
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
          {waveHeights.map((height, index) => (
            <span key={index} style={{ height }} />
          ))}
        </div>
        <div
          aria-label="Microphone input level"
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={micLevelPercent}
          className="agent-audio-input-meter"
          role="meter"
        >
          <span style={{ transform: `scaleX(${Math.max(0.04, micLevel)})` }} />
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

function getAudioContextConstructor(): BrowserAudioContextConstructor | undefined {
  const browserWindow = window as typeof window & {
    AudioContext?: BrowserAudioContextConstructor;
    webkitAudioContext?: BrowserAudioContextConstructor;
  };
  return browserWindow.AudioContext ?? browserWindow.webkitAudioContext;
}

function isAudioSurfaceActive(surface: AgentAudioSurface): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  const desktop = window.matchMedia(AUDIO_SURFACE_DESKTOP_QUERY).matches;
  return desktop ? surface === "drawer" : surface === "sheet";
}

function reserveOpeningGreeting(): boolean {
  const now = Date.now();
  if (now - lastOpeningGreetingAt < 1500) return false;
  lastOpeningGreetingAt = now;
  return true;
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

function formatMicrophoneError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError" || error.name === "SecurityError") return "Microphone permission was blocked.";
    if (error.name === "NotFoundError" || error.name === "OverconstrainedError") return "No microphone input was found.";
    if (error.name === "NotReadableError") return "Microphone input is already in use.";
  }
  return error instanceof Error ? error.message : "Microphone input could not start.";
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

function clampLevel(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function getWaveHeights(level: number): number[] {
  const base = 10;
  const gain = clampLevel(level);
  return [0.55, 0.8, 1, 0.74, 0.58].map((weight) => Math.round(base + gain * weight * 30));
}
