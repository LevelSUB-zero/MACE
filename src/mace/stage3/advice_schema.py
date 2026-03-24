"""
Module: advice_schema
Stage: 3
Purpose: Core data structures for the Advisory System. All schemas are
         strictly typed using dataclasses and include canonical
         serialization and HMAC signature capabilities.

Part of MACE (Meta Aware Cognitive Engine).
Spec: docs/phase3/advisory_system_spec.md § 3.1, 3.2
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

from mace.core import signing, canonical


@dataclass
class Stage3SignedObject:
    """Base class providing deterministic signing and serialization."""
    signature: Optional[str] = field(default=None, init=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None signatures to ensure clean signing."""
        d = asdict(self)
        if d.get("signature") is None:
            d.pop("signature", None)
        return d
        
    def sign(self, key_id: str = "stage3_advisory_key") -> str:
        """
        Sign the object using the canonical JSON representation of its fields
        (excluding the signature field itself).
        """
        payload = self.to_dict()
        payload.pop("signature", None)
        
        sig = signing.sign_payload(payload, key_id)
        self.signature = sig
        return sig
        
    def verify(self, key_id: str = "stage3_advisory_key") -> bool:
        """Verify the HMAC signature."""
        if not self.signature:
            return False
            
        payload = self.to_dict()
        payload.pop("signature", None)
        expected = signing.sign_payload(payload, key_id)
        
        return self.signature == expected


@dataclass
class AdviceObject(Stage3SignedObject):
    advice_id: str
    content: str
    advisory_confidence: float
    evidence_refs: List[str]
    source_module: str
    created_seeded_ts: str
    advisory_label: str = "advisory"


@dataclass
class AdviceQualityReport(Stage3SignedObject):
    report_id: str
    advice_id: str
    factuality: float
    relevance: float
    coherence: float
    provenance: float
    uncertainty: float
    novelty: float
    safety: str
    empirical_utility: float
    composite_score: float
    flags: List[str]
    created_seeded_ts: str
    derived_from_evidence: bool


@dataclass
class CouncilVote(Stage3SignedObject):
    member_id: str
    vote: str  # approve, reject, abstain
    rationale: str


@dataclass
class CouncilEvaluationRecord(Stage3SignedObject):
    request_id: str
    votes: List[Dict[str, Any]] # Stored as dicts (from CouncilVote.to_dict()) for clean serialization
    disagreement_summary: str
    final_recommendation: str
    created_seeded_ts: str


@dataclass
class ActionRequest(Stage3SignedObject):
    request_id: str
    requester: str
    action_type: str
    payload: Dict[str, Any]
    approved: bool
    created_seeded_ts: str
