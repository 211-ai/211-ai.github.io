import { useEffect, useRef, useState } from "react";
import { CircleAlert, Loader2, Pause, Play, Volume2 } from "lucide-react";
import { clientAudioReplyService, type ClientAudioReplyResult } from "../../lib/clientAudioReplyService";

type AudioBubbleState = "idle" | "loading" | "ready" | "speaking" | "failed";

export function AgentAudioBubble({ messageId, text }: { messageId: string; text: string }) {
  const [state, setState] = useState<AudioBubbleState>("idle");
  const [result, setResult] = useState<ClientAudioReplyResult | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      stopBrowserSpeech();
    };
  }, [audioUrl]);

  async function prepareAudio() {
    setState("loading");
    setError("");
    try {
      const nextResult = await clientAudioReplyService.generateAudio(text);
      setResult(nextResult);
      if (nextResult.kind === "audio") {
        const nextAudioUrl = URL.createObjectURL(nextResult.audioBlob);
        setAudioUrl((previousUrl) => {
          if (previousUrl) URL.revokeObjectURL(previousUrl);
          return nextAudioUrl;
        });
        setState("ready");
        return;
      }
      playBrowserSpeech(nextResult.text);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Audio reply failed.");
      setState("failed");
    }
  }

  function playBrowserSpeech(spokenText: string) {
    if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
      setError("Audio playback is not available in this browser.");
      setState("failed");
      return;
    }
    stopBrowserSpeech();
    const utterance = new SpeechSynthesisUtterance(spokenText);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.onend = () => setState("ready");
    utterance.onerror = () => {
      setError("Browser speech playback failed.");
      setState("failed");
    };
    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
    setState("speaking");
  }

  function stopBrowserSpeech() {
    if (utteranceRef.current && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      utteranceRef.current = null;
    }
  }

  function toggleSpeech() {
    if (!result || result.kind !== "browser-speech") return;
    if (state === "speaking") {
      stopBrowserSpeech();
      setState("ready");
      return;
    }
    playBrowserSpeech(result.text);
  }

  const label = getActionLabel(state, result);

  return (
    <div className="agent-audio-bubble" data-message-id={messageId}>
      <div className="agent-audio-visual" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
      </div>
      <div className="agent-audio-content">
        <div className="agent-audio-title">
          <Volume2 aria-hidden="true" size={16} />
          <span>{result?.modelName || "Audio reply"}</span>
        </div>
        {audioUrl ? (
          <audio controls preload="metadata" src={audioUrl}>
            <a href={audioUrl}>Open audio</a>
          </audio>
        ) : null}
        {result?.kind === "browser-speech" ? (
          <p className="agent-audio-note">{result.fallbackReason}</p>
        ) : null}
        {error ? (
          <p className="agent-audio-error">
            <CircleAlert aria-hidden="true" size={14} /> {error}
          </p>
        ) : null}
      </div>
      <button
        aria-label={label}
        className="agent-audio-action"
        disabled={state === "loading" || result?.kind === "audio"}
        onClick={result?.kind === "browser-speech" && state !== "idle" ? toggleSpeech : prepareAudio}
        type="button"
      >
        {state === "loading" ? (
          <Loader2 aria-hidden="true" className="agent-audio-spinner" size={16} />
        ) : state === "speaking" ? (
          <Pause aria-hidden="true" size={16} />
        ) : result ? (
          <Play aria-hidden="true" size={16} />
        ) : (
          <Volume2 aria-hidden="true" size={16} />
        )}
        <span>{label}</span>
      </button>
    </div>
  );
}

function getActionLabel(state: AudioBubbleState, result: ClientAudioReplyResult | null): string {
  if (state === "loading") return "Preparing";
  if (state === "speaking") return "Stop";
  if (!result) return "Audio";
  if (result.kind === "browser-speech") return "Play";
  return "Ready";
}
