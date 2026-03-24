"""
Stage 3 Self-Representation Registration

Bootstraps the registry of Stage 3 modules into the self-representation graph.
"""

from mace.self_representation.core import register_module, register_edge

STAGE3_MODULES = [
    {
        "module_id": "mace.stage3.advisory_events",
        "version": "1.0.0",
        "capabilities": ["event_logging"],
        "status": "active"
    },
    {
        "module_id": "mace.stage3.advice_schema",
        "version": "1.0.0",
        "capabilities": ["schema_validation", "hmac_signing"],
        "status": "active"
    },
    {
        "module_id": "mace.stage3.advice_quality",
        "version": "1.0.0",
        "capabilities": ["heuristic_evaluation"],
        "status": "active"
    },
    {
        "module_id": "mace.stage3.advice_ingestion",
        "version": "1.0.0",
        "capabilities": ["boundary_enforcement"],
        "status": "active"
    },
    {
        "module_id": "mace.stage3.council_evaluator",
        "version": "1.0.0",
        "capabilities": ["quorum_evaluation", "consensus_building"],
        "status": "active"
    },
    {
        "module_id": "mace.stage3.permission_boundary",
        "version": "1.0.0",
        "capabilities": ["output_filtering"],
        "status": "active"
    },
    {
        "module_id": "mace.stage3.meta_cognition_guard",
        "version": "1.0.0",
        "capabilities": ["reflection_guard", "parity_checking"],
        "status": "active"
    },
    {
        "module_id": "mace.stage3.halt_engine",
        "version": "1.0.0",
        "capabilities": ["emergency_halting", "investigation_assignment"],
        "status": "active"
    },
    {
        "module_id": "mace.stage3.advisory_pipeline",
        "version": "1.0.0",
        "capabilities": ["pipeline_orchestration"],
        "status": "active"
    }
]

def register_stage3_graph():
    for mod in STAGE3_MODULES:
        try:
            register_module(mod)
            print(f"Registered {mod['module_id']}")
        except Exception as e:
            print(f"Failed to register module {mod['module_id']}: {e}")

    print("Stage 3 Self-Representation registration complete.")

if __name__ == "__main__":
    register_stage3_graph()
