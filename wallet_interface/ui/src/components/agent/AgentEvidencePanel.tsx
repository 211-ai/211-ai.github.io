import { ChevronDown } from "lucide-react";
import type { EvidenceBundle } from "../../agent/types";
import { AgentCitationLink } from "./AgentCitationLink";

export interface AgentEvidencePanelProps {
  bundles: EvidenceBundle[];
  bundleIds?: string[];
  maxItemsPerBundle?: number;
  onOpenServiceDetail?: (docId: string) => void;
}

export function AgentEvidencePanel({
  bundles,
  bundleIds,
  maxItemsPerBundle = 6,
  onOpenServiceDetail
}: AgentEvidencePanelProps) {
  const selectedBundles = selectBundles(bundles, bundleIds);
  if (!selectedBundles.length) return null;

  return (
    <section className="agent-evidence-panel" aria-label="GraphRAG evidence">
      <header className="agent-evidence-panel-header">
        <strong>Evidence</strong>
        <span>{formatBundleSummary(selectedBundles)}</span>
      </header>

      <div className="agent-evidence-bundles">
        {selectedBundles.map((bundle) => (
          <details className="agent-evidence-bundle" key={bundle.id} open>
            <summary>
              <span>{bundle.query}</span>
              <ChevronDown aria-hidden="true" size={16} />
            </summary>

            <div className="agent-evidence-items">
              {bundle.items.slice(0, maxItemsPerBundle).map((item, index) => (
                <article className="agent-evidence-item" key={`${bundle.id}:${item.id}:${index}`}>
                  <AgentCitationLink
                    citation={normalizeCitationLabel(item.citation, index)}
                    onOpenServiceDetail={onOpenServiceDetail}
                    score={item.score}
                    source={item.source}
                    title={item.title}
                  />
                  <p>{item.snippet}</p>
                </article>
              ))}
            </div>

            {bundle.items.length > maxItemsPerBundle ? (
              <p className="agent-evidence-overflow">
                {bundle.items.length - maxItemsPerBundle} more evidence items are available in this bundle.
              </p>
            ) : null}

            {bundle.graphNodeIds?.length || bundle.graphEdgeIds?.length ? (
              <footer className="agent-evidence-graph-meta">
                {bundle.graphNodeIds?.length ? <span>{bundle.graphNodeIds.length} graph nodes</span> : null}
                {bundle.graphEdgeIds?.length ? <span>{bundle.graphEdgeIds.length} graph edges</span> : null}
              </footer>
            ) : null}
          </details>
        ))}
      </div>
    </section>
  );
}

function selectBundles(bundles: EvidenceBundle[], bundleIds?: string[]): EvidenceBundle[] {
  if (!bundleIds?.length) return [];
  const bundleById = new Map(bundles.map((bundle) => [bundle.id, bundle]));
  return bundleIds.map((id) => bundleById.get(id)).filter((bundle): bundle is EvidenceBundle => Boolean(bundle));
}

function normalizeCitationLabel(citation: EvidenceBundle["items"][number]["citation"], index: number) {
  if (citation.label.trim()) return citation;
  return {
    ...citation,
    label: `[${index + 1}]`
  };
}

function formatBundleSummary(bundles: EvidenceBundle[]): string {
  const itemCount = bundles.reduce((total, bundle) => total + bundle.items.length, 0);
  return `${itemCount} source${itemCount === 1 ? "" : "s"}`;
}
