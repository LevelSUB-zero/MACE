import json
import os
import datetime
import jsonschema
from mace.core import persistence, deterministic, canonical

# Load schema bundle
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "../../../schemas/ra9_schema_bundle.json")
_SCHEMA_BUNDLE = None

def _get_schema_bundle():
    global _SCHEMA_BUNDLE
    if _SCHEMA_BUNDLE is None:
        with open(SCHEMA_PATH, "r") as f:
            _SCHEMA_BUNDLE = json.load(f)
    return _SCHEMA_BUNDLE

def _validate_module(module_dict):
    bundle = _get_schema_bundle()
    resolver = jsonschema.RefResolver.from_schema(bundle)
    schema = bundle["definitions"]["SelfRepresentationNode"]
    jsonschema.validate(module_dict, schema, resolver=resolver)

def register_module(module_dict):
    """
    Register a new module or update existing one.
    """
    # 1. Validate Schema
    _validate_module(module_dict)
    
    module_id = module_dict["module_id"]
    version = module_dict.get("version", "1.0.0")
    
    # 2. Canonicalize for storage
    node_json = canonical.canonical_json_serialize(module_dict)
    
    # 3. DB Insert/Update
    conn = persistence.get_connection()
    try:
        # Check if exists
        cur = persistence.execute_query(conn, "SELECT module_id FROM self_representation_nodes WHERE module_id = ?", (module_id,))
        existing = persistence.fetch_one(cur)
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        if existing:
            # Update
            persistence.execute_query(conn, 
                "UPDATE self_representation_nodes SET node_json = ?, version = version + 1 WHERE module_id = ?",
                (node_json, module_id)
            )
        else:
            # Insert
            persistence.execute_query(conn,
                "INSERT INTO self_representation_nodes (module_id, node_json, created_at, version) VALUES (?, ?, ?, ?)",
                (module_id, node_json, timestamp, 1)
            )
        
        conn.commit()
        return True
    finally:
        conn.close()

def get_module(module_id):
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn, "SELECT node_json FROM self_representation_nodes WHERE module_id = ?", (module_id,))
        row = persistence.fetch_one(cur)
        if row:
            return json.loads(row["node_json"])
        return None
    finally:
        conn.close()

def decommission_module(module_id):
    conn = persistence.get_connection()
    try:
        # Get current
        cur = persistence.execute_query(conn, "SELECT node_json FROM self_representation_nodes WHERE module_id = ?", (module_id,))
        row = persistence.fetch_one(cur)
        if not row:
            return False
            
        module_dict = json.loads(row["node_json"])
        module_dict["status"] = "offline"
        
        node_json = canonical.canonical_json_serialize(module_dict)
        
        persistence.execute_query(conn, 
            "UPDATE self_representation_nodes SET node_json = ?, version = version + 1 WHERE module_id = ?",
            (node_json, module_id)
        )
        conn.commit()
        return True
    finally:
        conn.close()

def register_edge(from_module, to_module, edge_type="dependency"):
    """
    Register an edge between two modules in the self-representation graph.
    
    Args:
        from_module: Source module ID
        to_module: Target module ID
        edge_type: Type of relationship (dependency, calls, data_flow, etc.)
    """
    conn = persistence.get_connection()
    try:
        # Create edge dict
        edge_dict = {
            "from": from_module,
            "to": to_module,
            "edge_type": edge_type
        }
        
        # Generate deterministic edge ID
        edge_payload = canonical.canonical_json_serialize(edge_dict)
        edge_id = deterministic.deterministic_id("selfrep_edge", edge_payload)
        
        edge_dict["edge_id"] = edge_id
        
        # Canonicalize for storage
        edge_json = canonical.canonical_json_serialize(edge_dict)
        
        # Insert (ignore if exists)
        persistence.execute_query(conn,
            "INSERT OR IGNORE INTO self_representation_edges (edge_id, edge_json) VALUES (?, ?)",
            (edge_id, edge_json)
        )
        conn.commit()
        return edge_id
    finally:
        conn.close()

def graph_snapshot():
    """
    Return full graph snapshot with deterministic ID.
    """
    conn = persistence.get_connection()
    try:
        # Get all nodes
        cur = persistence.execute_query(conn, "SELECT node_json FROM self_representation_nodes")
        nodes = [json.loads(row["node_json"]) for row in persistence.fetch_all(cur)]
        
        # Get all edges
        cur = persistence.execute_query(conn, "SELECT edge_json FROM self_representation_edges")
        edges = [json.loads(row["edge_json"]) for row in persistence.fetch_all(cur)]
        
        # Sort for determinism
        nodes.sort(key=lambda x: x["module_id"])
        edges.sort(key=lambda x: (x["from"], x["to"]))
        
        snapshot = {
            "nodes": nodes,
            "edges": edges
        }
        
        # Generate ID
        # We use a deterministic counter for snapshots? Or just hash content?
        # Plan says: deterministic_id(seed, 'selfrep_snapshot', snapshot_json, counter)
        # We need a seed. If we are in a job, we have a seed. If global, maybe system seed?
        # For now, let's hash the content as payload.
        
        snapshot_json = canonical.canonical_json_serialize(snapshot)
        
        # If we don't have a global seed initialized, we might fail.
        # Assuming init_seed called by caller or we use a default.
        # Let's try to use a temporary seed if not set, or rely on caller.
        # But graph_snapshot might be called outside a job.
        # Let's use a "system" seed for structural snapshots if needed.
        
        if deterministic.get_seed() is None:
             deterministic.init_seed("system_snapshot_seed")
             
        snapshot_id = deterministic.deterministic_id("selfrep_snapshot", snapshot_json)
        
        return {
            "snapshot_id": snapshot_id,
            "snapshot": snapshot
        }
    finally:
        conn.close()
