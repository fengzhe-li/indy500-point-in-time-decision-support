from .config import RUN_RECORDED_AT
from .io_utils import stable_id, canonical_json, lineage_hash

class Provenance:
    def __init__(self):
        self.items = []
        self.links = []

    def item(self, source_id, locator, captured, source_timestamp=None, basis="UNKNOWN", note=None):
        item_id = stable_id("evidence_item", source_id, locator)
        self.items.append({"evidence_item_id": item_id, "source_id": source_id,
            "source_native_locator": locator, "captured_value_text": captured,
            "source_timestamp_utc": source_timestamp, "source_timestamp_basis": basis,
            "review_note": note})
        return item_id

    def observed(self, table, entity_id, field, evidence_item_id, classification="RAW_OBSERVED", primary=True, rule=None, version=None, note=None):
        self.links.append(self._link(table, entity_id, field, evidence_item_id, classification,
            primary, rule, version, None, None, None, note))

    def derived(self, table, entity_id, field, rule, version, lineage, refs):
        self.links.append(self._link(table, entity_id, field, None, "DERIVED_DETERMINISTIC",
            True, rule, version, canonical_json(lineage), canonical_json(refs), lineage_hash(lineage), None))

    def reconstructed(self, table, entity_id, field, evidence_item_id, rule, version, lineage, refs, note=None, primary=True):
        self.links.append(self._link(table, entity_id, field, evidence_item_id,
            "RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE", primary, rule, version,
            canonical_json(lineage), canonical_json(refs), lineage_hash(lineage), note))

    def supersede(self, table, entity_id, field):
        for link in self.links:
            if link["entity_table"] == table.upper() and link["entity_id"] == entity_id and link["field_name"] == field and link["is_primary"]:
                link["is_primary"] = False
                link["conflict_disposition"] = "SUPERSEDED"

    def _link(self, table, entity_id, field, evidence_id, classification, primary, rule, version, lineage, refs, snapshot, note):
        identity = len(self.links) + 1
        return {"field_evidence_link_id": stable_id("field_link", table, entity_id, field, identity),
            "entity_table": table.upper(), "entity_id": entity_id, "field_name": field,
            "evidence_item_id": evidence_id, "value_classification": classification,
            "is_primary": primary, "conflict_disposition": "PRIMARY" if primary else "CORROBORATING",
            "derivation_rule_id": rule, "derivation_rule_version": version,
            "input_lineage_json": lineage, "input_entity_field_refs_json": refs,
            "input_snapshot_hash": snapshot, "uncertainty_note": note,
            "reviewer_id": "PIPELINE_V1" if classification == "MANUALLY_ANNOTATED" else None,
            "recorded_at_utc": RUN_RECORDED_AT}
