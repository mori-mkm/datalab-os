"""Analytics department: Analytics Lead -> EDA Analyst -> Hypothesis Analyst."""

from datalab.agents import analytics_lead, eda_analyst, hypothesis_analyst
from datalab.graphs.spec import AgentSpec, DepartmentSpec

SPEC = DepartmentSpec(
    id="analytics",
    label="Analytics",
    role="Explores the data and derives hypotheses",
    agents=(
        AgentSpec("analytics_lead", "Analytics Lead", "Checks prerequisites, delegates", analytics_lead.run),
        AgentSpec("eda_analyst", "EDA Analyst", "Summaries and correlations", eda_analyst.run),
        AgentSpec("hypothesis_analyst", "Hypothesis Analyst", "Data-driven hypotheses", hypothesis_analyst.run),
    ),
)
