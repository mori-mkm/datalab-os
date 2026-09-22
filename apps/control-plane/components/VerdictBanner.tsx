// Shared by the Results and Review tabs: APPROVED and REJECTED must be equally prominent, never softened.
// Renders the verdict string verbatim -- no client-authored wording about why.
export function VerdictBanner({ verdict }: { verdict: string | null }) {
  if (!verdict) return <div className="verdict verdict--pending">Not yet reviewed.</div>;
  const approved = verdict === "APPROVED";
  return <div className={`verdict ${approved ? "verdict--approved" : "verdict--rejected"}`}>{verdict}</div>;
}
