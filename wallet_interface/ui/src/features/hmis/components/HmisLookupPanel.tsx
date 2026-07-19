import { useMemo, useState } from "react";
import { Badge, Button, Card, Field, Section, StatusBanner } from "../../../shared/components/ui";
import type { WalletApiConfig } from "../../wallet/lib/walletApi";
import {
  listHmisProgramLinks,
  lookupHmisClients,
  lookupHmisHouseholds,
  type WalletHmisOperationResult
} from "../../wallet/lib/walletApi";

interface HmisLookupPanelProps {
  apiConfig?: WalletApiConfig;
  onSelectCandidate?: (candidate: Record<string, unknown>) => void;
}

function resultRows(result: WalletHmisOperationResult): Array<Record<string, unknown>> {
  if (result.clients?.length) return result.clients;
  if (result.households?.length) return result.households;
  if (result.programs?.length) return result.programs;
  return [];
}

export function HmisLookupPanel({ apiConfig, onSelectCandidate }: HmisLookupPanelProps) {
  const [name, setName] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [programRef, setProgramRef] = useState("");
  const [mode, setMode] = useState<"clients" | "households" | "programs">("clients");
  const [result, setResult] = useState<WalletHmisOperationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const rows = useMemo(() => (result ? resultRows(result) : []), [result]);

  async function runLookup() {
    if (!apiConfig) {
      setError("Wallet API configuration is required for HMIS lookup.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const nextResult =
        mode === "clients"
          ? await lookupHmisClients(apiConfig, { name, dateOfBirth, programRef })
          : mode === "households"
            ? await lookupHmisHouseholds(apiConfig, { name, programRef })
            : await listHmisProgramLinks(apiConfig, { name, programRef });
      setResult(nextResult);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "HMIS lookup failed.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section title="HMIS lookup" eyebrow="Phase 2 · Read-only search">
      <div className="chip-grid" aria-label="HMIS lookup mode">
        {(["clients", "households", "programs"] as const).map((value) => (
          <button className="choice-chip" key={value} onClick={() => setMode(value)} type="button">
            {value}
          </button>
        ))}
      </div>
      <div className="form-grid">
        <Field label="Name">
          <input onChange={(event) => setName(event.target.value)} placeholder="Jane Doe" value={name} />
        </Field>
        <Field label="Date of birth">
          <input onChange={(event) => setDateOfBirth(event.target.value)} placeholder="1990-04-05" value={dateOfBirth} />
        </Field>
        <Field label="Program reference">
          <input onChange={(event) => setProgramRef(event.target.value)} placeholder="shelter-a" value={programRef} />
        </Field>
      </div>
      <div className="row-actions">
        <Button disabled={!name.trim() && !programRef.trim()} loading={loading} onClick={() => void runLookup()}>
          Run HMIS lookup
        </Button>
      </div>
      {error ? <StatusBanner tone="warning">{error}</StatusBanner> : null}
      {result?.summary ? <StatusBanner tone="info">{result.summary}</StatusBanner> : null}
      <div className="list-stack">
        {rows.map((row, index) => {
          const lastSync = typeof row.last_sync_at === "string" ? row.last_sync_at : "Not synced";
          const score = typeof row.score === "number" ? row.score.toFixed(2) : undefined;
          return (
            <Card
              actions={
                onSelectCandidate ? (
                  <Button onClick={() => onSelectCandidate(row)} variant="secondary">
                    Review
                  </Button>
                ) : undefined
              }
              key={`${String(row.external_id ?? row.external_project_id ?? index)}`}
              title={String(row.name ?? row.household_name ?? row.program_name ?? row.external_id ?? "HMIS record")}
            >
              <p>{String(row.provider_name ?? row.program_name ?? row.program_ref ?? "Masked candidate result")}</p>
              <div className="badge-row">
                <Badge>{mode}</Badge>
                <Badge tone="info">{String(row.link_status ?? row.status ?? "unlinked")}</Badge>
                {score ? <Badge tone="success">score {score}</Badge> : null}
              </div>
              <small className="upload-machine-summary">Last sync: {lastSync}</small>
            </Card>
          );
        })}
      </div>
    </Section>
  );
}
