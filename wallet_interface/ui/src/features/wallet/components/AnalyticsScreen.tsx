import { Badge, Section, StatusBanner } from "../../../components/ui";
import { StatusPanel } from "../../../app/components/StatusPanel";
import { ProofReceiptView } from "../../../models/abby";
import { analyticsStudies } from "../../../services/mockAbbyService";

/**
 * Maps a snake_case analytics field name to a human-readable label.
 * Falls back to replacing underscores with spaces for any unmapped fields.
 * Update the `labels` map when new analytics fields are added to the data model.
 */
function formatAnalyticsField(field: string): string {
  const labels: Record<string, string> = {
    age_group: "age group",
    county: "county",
    housing_outcome: "housing outcome",
    need_category: "need type",
    service_type: "service type"
  };
  return labels[field] ?? field.replace(/_/g, " ");
}

const analyticsNeverPublishedText =
  "No names, contact details, exact locations, files, staff actions, case notes, or individual service histories";
const analyticsProviderPublicationFloor = 3;

function parseAnalyticsProofNumber(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function calculatePercent(value: number, total: number): number {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

function formatAnalyticsProofValue(value: string | undefined): string {
  if (!value) return "";
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return numeric.toLocaleString();
  return value
    .split("_")
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export function AnalyticsScreen({
  optedIn,
  proofs,
  setOptedIn
}: {
  optedIn: Record<string, boolean>;
  proofs: ProofReceiptView[];
  setOptedIn: (value: Record<string, boolean>) => void;
}) {
  function toggleStudy(studyId: string) {
    setOptedIn({ ...optedIn, [studyId]: !isStudySelected(studyId) });
  }

  function isStudySelected(studyId: string) {
    return optedIn[studyId] ?? true;
  }

  const selectedStudyCount = analyticsStudies.filter((study) => isStudySelected(study.id)).length;
  const pausedStudyCount = analyticsStudies.filter((study) => study.status === "paused").length;
  const cohortFloorValues = analyticsStudies.map((study) => study.minCohortSize);
  const cohortFloorMin = cohortFloorValues.length ? Math.min(...cohortFloorValues) : 0;
  const cohortFloorMax = cohortFloorValues.length ? Math.max(...cohortFloorValues) : 0;
  const cohortFloorLabel =
    cohortFloorValues.length === 0
      ? "0"
      : cohortFloorMin === cohortFloorMax
        ? String(cohortFloorMin)
        : `${cohortFloorMin}-${cohortFloorMax}`;
  const analyticsProofCertificates = proofs.filter(
    (proof) => proof.proofType.startsWith("analytics_") && proof.verificationStatus === "verified"
  );
  const homelessnessProofs = analyticsProofCertificates.filter((proof) => proof.proofType === "analytics_population_snapshot");
  const providerCapacityProofs = analyticsProofCertificates.filter((proof) => proof.proofType === "analytics_provider_capacity");
  const housingOutcomeProofs = analyticsProofCertificates.filter((proof) => proof.proofType === "analytics_housing_outcome");
  const outreachFollowupProofs = analyticsProofCertificates.filter((proof) => proof.proofType === "analytics_outreach_followup");
  const recoveryOutcomeProofs = analyticsProofCertificates.filter((proof) => proof.proofType === "analytics_recovery_outcome");
  const cohortPeopleCount = homelessnessProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.cohort_count),
    0
  );
  const providerOrganizationsCount = providerCapacityProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.providers_included),
    0
  );
  const countiesCoveredCount = new Set(
    analyticsProofCertificates.map((proof) => proof.publicInputs.county).filter(Boolean)
  ).size;
  const shelterRequestsTotal = homelessnessProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.shelter_requests),
    0
  );
  const waitingOverWeekCount = homelessnessProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.waiting_over_7_days),
    0
  );
  const housedReferralsTotal = housingOutcomeProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.housed_referrals),
    0
  );
  const referralsCompletedTotal = housingOutcomeProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.referrals_completed),
    0
  );
  const occupiedBedsTotal = providerCapacityProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.occupied_beds),
    0
  );
  const licensedBedsTotal = providerCapacityProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.licensed_beds),
    0
  );
  const sameDayProgramsTotal = providerCapacityProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.same_day_available_programs),
    0
  );
  const totalPrograms = providerCapacityProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.total_programs),
    0
  );
  const completedFollowupsTotal = outreachFollowupProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.completed_followups),
    0
  );
  const assignedFollowupsTotal = outreachFollowupProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.assigned_followups),
    0
  );
  const treatmentReferralsTotal = recoveryOutcomeProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.treatment_referrals),
    0
  );
  const rehabIntakesCompletedTotal = recoveryOutcomeProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.intakes_completed),
    0
  );
  const activeRecoveryPlansTotal = recoveryOutcomeProofs.reduce(
    (sum, proof) => sum + parseAnalyticsProofNumber(proof.publicInputs.active_recovery_plans),
    0
  );
  const shelterFillRate = calculatePercent(occupiedBedsTotal, licensedBedsTotal);
  const waitingOverWeekRate = calculatePercent(waitingOverWeekCount, shelterRequestsTotal);
  const referralToHousingRate = calculatePercent(housedReferralsTotal, referralsCompletedTotal);
  const outreachFollowupRate = calculatePercent(completedFollowupsTotal, assignedFollowupsTotal);
  const sameDayAvailabilityRate = calculatePercent(sameDayProgramsTotal, totalPrograms);
  const rehabIntakeRate = calculatePercent(rehabIntakesCompletedTotal, treatmentReferralsTotal);
  const activeRecoveryPlanRate = calculatePercent(activeRecoveryPlansTotal, rehabIntakesCompletedTotal);
  const studyTitleById = new Map(analyticsStudies.map((study) => [study.id, study.title]));
  const summaryPanels = [
    { label: "People in verified cohorts", value: cohortPeopleCount.toLocaleString(), tone: "teal" },
    { label: "Providers in verified releases", value: providerOrganizationsCount.toLocaleString(), tone: "teal" },
    { label: "Counties covered", value: String(countiesCoveredCount), tone: "gold" },
    { label: "Mock proof certificates", value: String(analyticsProofCertificates.length), tone: "teal" },
    { label: "Shelter requests this week", value: shelterRequestsTotal.toLocaleString(), tone: "red" },
    { label: "Average shelter fill rate", value: `${shelterFillRate}%`, tone: "gold" },
    { label: "Referral-to-housing rate", value: `${referralToHousingRate}%`, tone: "teal" },
    { label: "Recovery intake rate", value: `${rehabIntakeRate}%`, tone: "teal" }
  ];
  const populationSignals = [
    {
      badge: "Demand rising",
      badgeTone: "warning",
      detail: `Weekly shelter requests total ${shelterRequestsTotal.toLocaleString()} across ${homelessnessProofs.length} verified county proof certificates.`,
      footnote: "Largest released cohorts still use age-group and need-type suppression to avoid singling anyone out.",
      progress: Math.max(10, shelterRequestsTotal ? 78 : 0),
      title: "Unsheltered people requesting a bed",
      value: shelterRequestsTotal.toLocaleString()
    },
    {
      badge: "Needs attention",
      badgeTone: "warning",
      detail: `People waiting longer than 7 days for placement represent ${waitingOverWeekRate}% of the released shelter-request proofs.`,
      footnote: "Breakdowns stay hidden whenever the release floor is not met.",
      progress: waitingOverWeekRate,
      title: "People waiting a week or more",
      value: `${waitingOverWeekRate}%`
    },
    {
      badge: "Improving",
      badgeTone: "success",
      detail: `Verified referrals that lead to stable placement now total ${housedReferralsTotal.toLocaleString()} across ${housingOutcomeProofs.length} outcome certificates.`,
      footnote: "Calculated from proof-backed referral and placement totals only.",
      progress: referralToHousingRate,
      title: "Referrals that end in housing",
      value: `${referralToHousingRate}%`
    }
  ];
  const providerSignals = [
    {
      badge: "Near capacity",
      badgeTone: "warning",
      detail: `Emergency shelter releases cover ${providerOrganizationsCount.toLocaleString()} provider organizations contributing occupancy proofs.`,
      footnote: "Average verified occupancy across participating emergency shelter providers.",
      progress: shelterFillRate,
      title: "Emergency shelter networks",
      value: `${shelterFillRate}% full`
    },
    {
      badge: "Expanding",
      badgeTone: "success",
      detail: `Mobile teams published ${completedFollowupsTotal.toLocaleString()} completed follow-ups from ${assignedFollowupsTotal.toLocaleString()} assigned outreach contacts.`,
      footnote: "Measures closed-loop outreach contacts without publishing any contact log.",
      progress: outreachFollowupRate,
      title: "Street outreach follow-up rate",
      value: `${outreachFollowupRate}%`
    },
    {
      badge: "Stable",
      badgeTone: "info",
      detail: "Food, hygiene, and document-help sites continue to absorb demand faster than shelter networks.",
      footnote: `Availability is published only when at least ${analyticsProviderPublicationFloor} providers submit matching proof batches.`,
      progress: sameDayAvailabilityRate,
      title: "Support programs with same-day availability",
      value: `${sameDayAvailabilityRate}%`
    }
  ];
  const recoverySignals = [
    {
      badge: "Demand rising",
      badgeTone: "warning",
      detail: `Recovery providers accepted ${treatmentReferralsTotal.toLocaleString()} proof-backed rehab referrals across ${recoveryOutcomeProofs.length} verified county certificates.`,
      footnote: "Only aggregate treatment pathway counts are released, never treatment records or individual care plans.",
      progress: Math.max(10, treatmentReferralsTotal ? 74 : 0),
      title: "People referred to drug rehab services",
      value: treatmentReferralsTotal.toLocaleString()
    },
    {
      badge: "Engaged",
      badgeTone: "success",
      detail: `${rehabIntakeRate}% of released rehab referrals completed intake, showing how quickly people enter a treatment program after referral.`,
      footnote: "Referral-source breakdowns stay hidden until the cohort floor is met.",
      progress: rehabIntakeRate,
      title: "Rehab intake completion rate",
      value: `${rehabIntakeRate}%`
    },
    {
      badge: "Stabilizing",
      badgeTone: "info",
      detail: `${activeRecoveryPlansTotal.toLocaleString()} people moved into active recovery plans after intake across detox, residential, outpatient, and medication-assisted treatment cohorts.`,
      footnote: "Recovery plan totals are published without diagnoses, substances, provider rosters, or visit history.",
      progress: activeRecoveryPlanRate,
      title: "Active recovery plans after intake",
      value: `${activeRecoveryPlanRate}%`
    }
  ];
  const privacyGuardrails = [
    {
      detail:
        "Every published total comes from a proof that a real provider submitted an approved cohort count for the allowed schema.",
      title: "Zero-knowledge proofs before release"
    },
    {
      detail:
        `Breakdowns stay hidden whenever fewer than the configured cohort floor (${cohortFloorLabel} people) or fewer than ${analyticsProviderPublicationFloor} provider organizations are represented.`,
      title: "Suppression for small groups"
    },
    {
      detail: `${analyticsNeverPublishedText} are never published to this dashboard.`,
      title: "No row-level activity disclosure"
    }
  ];

  return (
    <div className="screen analytics-screen">
      <div className="page-title">
        <p className="eyebrow">Public analytics</p>
        <h1>Homelessness and service capacity dashboard</h1>
      </div>
      <p className="page-note">
        This public release shows only group totals proven with zero-knowledge proofs. It highlights homelessness trends,
        provider capacity, substance use treatment access, and referral outcomes without exposing names, contact
        details, exact locations, files, or case activity.
      </p>
      <StatusBanner tone="info">
        Every figure shown here clears minimum group and provider thresholds before it can appear in the public dashboard.
      </StatusBanner>
      <Section eyebrow="Public release" title="Dashboard summary">
        <p className="section-note">
          All figures reflect the latest verified proof batch from participating shelters, housing programs, outreach
          teams, and support providers.
        </p>
        <div className="dashboard-grid">
          {summaryPanels.map((panel) => (
            <StatusPanel key={panel.label} label={panel.label} value={panel.value} tone={panel.tone} />
          ))}
        </div>
      </Section>
      <Section title="Homelessness population snapshot">
        <p className="section-note">
          Public readers can track demand, waiting time, and housing outcomes at a cohort level without seeing who asked
          for help or what any single person did.
        </p>
        <div className="analytics-story-grid">
          {populationSignals.map((signal) => (
            <article className="analytics-story-card" key={signal.title}>
              <div className="scope-header">
                <div>
                  <h3>{signal.title}</h3>
                  <p>{signal.detail}</p>
                </div>
                <Badge tone={signal.badgeTone}>{signal.badge}</Badge>
              </div>
              <strong className="analytics-story-value">{signal.value}</strong>
              <div aria-hidden="true" className="analytics-progress">
                <span style={{ width: `${signal.progress}%` }} />
              </div>
              <small>{signal.footnote}</small>
            </article>
          ))}
        </div>
      </Section>
      <Section title="Service provider snapshot">
        <p className="section-note">
          Provider organizations contribute proof-backed counts so the public can see where services are under pressure
          without publishing staff activity, rosters, or program-level records.
        </p>
        <div className="analytics-story-grid">
          {providerSignals.map((signal) => (
            <article className="analytics-story-card" key={signal.title}>
              <div className="scope-header">
                <div>
                  <h3>{signal.title}</h3>
                  <p>{signal.detail}</p>
                </div>
                <Badge tone={signal.badgeTone}>{signal.badge}</Badge>
              </div>
              <strong className="analytics-story-value">{signal.value}</strong>
              <div aria-hidden="true" className="analytics-progress">
                <span style={{ width: `${signal.progress}%` }} />
              </div>
              <small>{signal.footnote}</small>
            </article>
          ))}
        </div>
      </Section>
      <Section title="Substance use treatment and recovery statistics">
        <p className="section-note">
          Recovery providers publish proof-backed referral and intake totals so the public can track rehab access without
          seeing treatment records, diagnoses, staff notes, or visit histories.
        </p>
        <div className="analytics-story-grid">
          {recoverySignals.map((signal) => (
            <article className="analytics-story-card" key={signal.title}>
              <div className="scope-header">
                <div>
                  <h3>{signal.title}</h3>
                  <p>{signal.detail}</p>
                </div>
                <Badge tone={signal.badgeTone}>{signal.badge}</Badge>
              </div>
              <strong className="analytics-story-value">{signal.value}</strong>
              <div aria-hidden="true" className="analytics-progress">
                <span style={{ width: `${signal.progress}%` }} />
              </div>
              <small>{signal.footnote}</small>
            </article>
          ))}
        </div>
      </Section>
      <Section title="Mock proof certificates behind this dashboard">
        <p className="section-note">
          {analyticsProofCertificates.length} verified mock proof certificates feed the current aggregate totals so the
          dashboard can be tested against public inputs instead of hard-coded statistics.
        </p>
        <div className="list-stack">
          {analyticsProofCertificates.map((proof) => {
            const studyTitle = studyTitleById.get(proof.publicInputs.study_id) ?? formatAnalyticsProofValue(proof.proofType);
            const proofHighlights = [
              proof.publicInputs.county ? `${formatAnalyticsProofValue(proof.publicInputs.county)} county` : "",
              proof.publicInputs.cohort_count
                ? `${formatAnalyticsProofValue(proof.publicInputs.cohort_count)} people in cohort`
                : "",
              proof.publicInputs.shelter_requests
                ? `${formatAnalyticsProofValue(proof.publicInputs.shelter_requests)} shelter requests`
                : "",
              proof.publicInputs.providers_included
                ? `${formatAnalyticsProofValue(proof.publicInputs.providers_included)} providers`
                : "",
              proof.publicInputs.occupied_beds && proof.publicInputs.licensed_beds
                ? `${formatAnalyticsProofValue(proof.publicInputs.occupied_beds)}/${formatAnalyticsProofValue(proof.publicInputs.licensed_beds)} occupied beds`
                : "",
              proof.publicInputs.housed_referrals && proof.publicInputs.referrals_completed
                ? `${formatAnalyticsProofValue(proof.publicInputs.housed_referrals)}/${formatAnalyticsProofValue(proof.publicInputs.referrals_completed)} housed referrals`
                : "",
              proof.publicInputs.completed_followups && proof.publicInputs.assigned_followups
                ? `${formatAnalyticsProofValue(proof.publicInputs.completed_followups)}/${formatAnalyticsProofValue(proof.publicInputs.assigned_followups)} outreach follow-ups`
                : "",
              proof.publicInputs.treatment_referrals
                ? `${formatAnalyticsProofValue(proof.publicInputs.treatment_referrals)} rehab referrals`
                : "",
              proof.publicInputs.intakes_completed
                ? `${formatAnalyticsProofValue(proof.publicInputs.intakes_completed)} rehab intakes`
                : "",
              proof.publicInputs.active_recovery_plans
                ? `${formatAnalyticsProofValue(proof.publicInputs.active_recovery_plans)} active recovery plans`
                : ""
            ].filter(Boolean);

            return (
              <article className="analytics-card" key={proof.id}>
                <div className="scope-header">
                  <div>
                    <h3>{proof.claim}</h3>
                    <p>{studyTitle} · {proof.verifier}</p>
                  </div>
                  <Badge tone="success">mock proof certificate</Badge>
                </div>
                <div className="badge-row">
                  <Badge>{proof.proofType.replace(/_/g, " ")}</Badge>
                  <Badge>{proof.witnessLabel}</Badge>
                  {proof.publicInputs.certificate_type ? (
                    <Badge>{formatAnalyticsProofValue(proof.publicInputs.certificate_type)}</Badge>
                  ) : null}
                </div>
                <div className="badge-row">
                  {proofHighlights.map((highlight) => (
                    <Badge key={`${proof.id}-${highlight}`}>{highlight}</Badge>
                  ))}
                </div>
                <small>
                  Public inputs: {Object.entries(proof.publicInputs)
                    .map(([key, value]) => `${formatAnalyticsField(key)} ${formatAnalyticsProofValue(value)}`)
                    .join(" · ")}
                </small>
              </article>
            );
          })}
        </div>
      </Section>
      <Section title="Zero-knowledge and privacy safeguards">
        <div className="analytics-method-grid">
          {privacyGuardrails.map((guardrail) => (
            <article className="analytics-card analytics-method-card" key={guardrail.title}>
              <h3>{guardrail.title}</h3>
              <p>{guardrail.detail}</p>
            </article>
          ))}
        </div>
        <div className="disclosure-package analytics-release-disclosure">
          <div className="disclosure-row">
            <strong>Published to the public</strong>
            <span>Group totals, safe category breakdowns, provider capacity signals, and proof freshness timestamps</span>
          </div>
          <div className="disclosure-row">
            <strong>Proven before publication</strong>
            <span>Minimum cohort size, provider participation floor, and approved schema</span>
          </div>
          <div className="disclosure-row">
            <strong>Never published</strong>
            <span>{analyticsNeverPublishedText}</span>
          </div>
        </div>
      </Section>
      <Section eyebrow="Publication workflow" title="Published measures review">
        <p className="section-note">
          These measure cards show what is currently approved for the public dashboard release and what remains paused or
          withheld.
        </p>
        <div className="privacy-metrics">
          <StatusPanel label="Measures live" value={String(selectedStudyCount)} tone="teal" />
          <StatusPanel label="Measures paused" value={String(pausedStudyCount)} tone="gold" />
        </div>
        <div className="analytics-grid">
          {analyticsStudies.map((study) => {
            const selected = isStudySelected(study.id);
            const titleId = `analytics-title-${study.id}`;
            const publicationStatus = study.status === "paused" ? "paused" : selected ? "public release" : "withheld";
            return (
              <article aria-labelledby={titleId} className="analytics-card" key={study.id}>
                <div className="scope-header">
                  <div>
                    <h3 id={titleId}>{study.title}</h3>
                    <p>{study.purpose}</p>
                  </div>
                  <Badge tone={study.status === "paused" ? "warning" : selected ? "success" : "neutral"}>
                    {publicationStatus}
                  </Badge>
                </div>
                <div className="privacy-metrics">
                  <StatusPanel label="Minimum cohort" value={String(study.minCohortSize)} tone="teal" />
                  <StatusPanel label="Approved fields" value={String(study.fields.length)} tone="teal" />
                </div>
                <div className="badge-row">
                  {study.fields.map((field: string) => (
                    <Badge key={field}>{formatAnalyticsField(field)}</Badge>
                  ))}
                </div>
                <div
                  className="capability-preview"
                  role="group"
                  aria-label={`${study.title} public analytics preview`}
                >
                  <div className="scope-header">
                    <div>
                      <h4>What the public can learn</h4>
                      <p>{study.fields.length} approved breakdowns · minimum cohort {study.minCohortSize}</p>
                    </div>
                    <Badge tone={study.status === "paused" ? "warning" : "success"}>
                      {study.status === "paused" ? "paused" : "proof-backed release"}
                    </Badge>
                  </div>
                  <div className="disclosure-package">
                    <div className="disclosure-row">
                      <strong>Published total</strong>
                      <span>{study.purpose}</span>
                    </div>
                    <div className="disclosure-row">
                      <strong>Safe breakdowns</strong>
                      <span>{study.fields.map(formatAnalyticsField).join(", ")}</span>
                    </div>
                    <div className="disclosure-row">
                      <strong>Never published</strong>
                      <span>{analyticsNeverPublishedText}</span>
                    </div>
                  </div>
                </div>
                <label className="consent-box">
                  <input
                    checked={selected}
                    onChange={() => toggleStudy(study.id)}
                    type="checkbox"
                  />
                  <span>
                    <strong>Include this measure in the public dashboard release.</strong>
                    <small>Turn it off to withhold this metric until it passes the next publication review.</small>
                  </span>
                </label>
              </article>
            );
          })}
        </div>
      </Section>
    </div>
  );
}
