import { AlertCircle, CheckCircle2, Clock, FileCheck2 } from "lucide-react";
import type { AgentToolCall, AgentToolResult } from "../../agent/types";

export interface AgentToolResultCardProps {
  result: AgentToolResult;
  toolCall?: AgentToolCall;
}

export function AgentToolResultCard({ result, toolCall }: AgentToolResultCardProps) {
  const summary = summarizeResult(result);
  const Icon = result.success ? CheckCircle2 : AlertCircle;

  return (
    <section
      aria-label={`${result.success ? "Completed" : "Failed"} tool result: ${summary.title}`}
      className={`agent-tool-result-card agent-tool-result-${result.success ? "success" : "failed"}`}
    >
      <header className="agent-card-header">
        <span className="agent-card-icon" aria-hidden="true">
          <Icon size={18} />
        </span>
        <div>
          <strong>{summary.title}</strong>
          <small>{result.success ? "Completed" : "Failed"}</small>
        </div>
      </header>

      <p className="agent-card-summary">{summary.message}</p>

      <dl className="agent-result-summary">
        <div>
          <dt>Request</dt>
          <dd>{toolCall ? summarizeToolInput(toolCall) : result.name}</dd>
        </div>
        <div>
          <dt>Result</dt>
          <dd>{result.success ? "Action completed." : result.error?.message ?? "Action failed."}</dd>
        </div>
      </dl>

      <footer className="agent-tool-result-footer">
        <span>
          <Clock aria-hidden="true" size={14} />
          {formatDateTime(result.completedAt)}
        </span>
        {result.auditEventId ? (
          <span>
            <FileCheck2 aria-hidden="true" size={14} />
            Audit recorded
          </span>
        ) : null}
      </footer>
    </section>
  );
}

interface ResultSummary {
  title: string;
  message: string;
}

function summarizeResult(result: AgentToolResult): ResultSummary {
  const output = result.output;
  if (isRecord(output)) {
    if (output.ok === true && typeof output.summary === "string") {
      return {
        title: readableName(result.name),
        message: output.summary
      };
    }
    if (output.ok === false && typeof output.message === "string") {
      return {
        title: readableName(result.name),
        message: output.message
      };
    }
  }

  return {
    title: readableName(result.name),
    message: result.success ? "The requested action completed." : result.error?.message ?? "The requested action failed."
  };
}

function summarizeToolInput(toolCall: AgentToolCall): string {
  if (!isRecord(toolCall.input)) return readableName(toolCall.name);
  const values = Object.entries(toolCall.input)
    .filter(([, value]) => value !== undefined)
    .slice(0, 3)
    .map(([key, value]) => `${formatFieldName(key)}: ${formatValue(value)}`);
  return values.length ? values.join("; ") : readableName(toolCall.name);
}

function readableName(value: string): string {
  return value.replace(/[_-]+/g, " ");
}

function formatFieldName(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .toLowerCase();
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return `${value.length} selected`;
  if (typeof value === "boolean") return value ? "on" : "off";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value.trim() || "blank";
  return "set";
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short"
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
