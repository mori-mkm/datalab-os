export type TabId = "overview" | "data" | "execution" | "collaboration" | "artifacts" | "results" | "review" | "report";

// All tabs are built now.
const TABS: { id: TabId; label: string; enabled: boolean }[] = [
  { id: "overview", label: "Overview", enabled: true },
  { id: "data", label: "Data", enabled: true },
  { id: "execution", label: "Execution", enabled: true },
  { id: "collaboration", label: "Collaboration", enabled: true },
  { id: "artifacts", label: "Artifacts", enabled: true },
  { id: "results", label: "Results", enabled: true },
  { id: "review", label: "Review", enabled: true },
  { id: "report", label: "Report", enabled: true },
];

export function TabNav({ active, onSelect }: { active: TabId; onSelect: (id: TabId) => void }) {
  return (
    <nav className="tabs">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`tabs__item ghost ${active === tab.id ? "tabs__item--active" : ""}`}
          disabled={!tab.enabled}
          aria-current={active === tab.id}
          onClick={() => onSelect(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
