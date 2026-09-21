"""Data Science department (id `modeling`): DS Lead -> Baseline Modeler -> Model Evaluator."""

from datalab.agents import baseline_modeler, ds_lead, model_evaluator
from datalab.graphs.spec import AgentSpec, DepartmentSpec

SPEC = DepartmentSpec(
    id="modeling",
    label="Data Science",
    role="Trains and evaluates the baseline model",
    agents=(
        AgentSpec("ds_lead", "DS Lead", "Checks prerequisites, plans the experiment", ds_lead.run),
        AgentSpec("baseline_modeler", "Baseline Modeler", "Trains the Logistic Regression", baseline_modeler.run),
        AgentSpec("model_evaluator", "Model Evaluator", "Evaluates the experiment", model_evaluator.run),
    ),
)
