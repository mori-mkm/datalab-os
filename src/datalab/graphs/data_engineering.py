"""Data Engineering department: Engineering Lead -> Data Profiler -> Data Quality Analyst."""

from datalab.agents import data_profiler, data_quality_analyst, engineering_lead
from datalab.graphs.spec import AgentSpec, DepartmentSpec

SPEC = DepartmentSpec(
    id="data_engineering",
    label="Data Engineering",
    role="Profiles the dataset and assesses its quality",
    agents=(
        AgentSpec("engineering_lead", "Engineering Lead", "Validates the schema, delegates", engineering_lead.run),
        AgentSpec("data_profiler", "Data Profiler", "Computes the structural profile", data_profiler.run),
        AgentSpec("data_quality_analyst", "Data Quality Analyst", "Assesses data quality", data_quality_analyst.run),
    ),
)
