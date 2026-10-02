from app.agent.claims import (
    validate_claim,
    validate_claims,
    validate_evidence_reference,
)


def test_valid_evidence_reference():
    evidence = {
        "regional_performance": [
            {
                "region": "South",
                "revenue": 120000,
            },
            {
                "region": "West",
                "revenue": 100000,
            },
        ]
    }

    reference = {
        "investigation": "regional_performance",
        "field": "revenue",
        "entity": "South",
    }

    assert validate_evidence_reference(
        reference,
        evidence,
    ) is True


def test_reference_requires_existing_investigation():
    evidence = {
        "regional_performance": [
            {
                "region": "South",
                "revenue": 120000,
            }
        ]
    }

    reference = {
        "investigation": "customer_segments",
        "field": "revenue",
        "entity": "South",
    }

    assert validate_evidence_reference(
        reference,
        evidence,
    ) is False


def test_reference_requires_existing_field():
    evidence = {
        "regional_performance": [
            {
                "region": "South",
                "revenue": 120000,
            }
        ]
    }

    reference = {
        "investigation": "regional_performance",
        "field": "profit",
        "entity": "South",
    }

    assert validate_evidence_reference(
        reference,
        evidence,
    ) is False


def test_reference_requires_existing_entity():
    evidence = {
        "regional_performance": [
            {
                "region": "South",
                "revenue": 120000,
            }
        ]
    }

    reference = {
        "investigation": "regional_performance",
        "field": "revenue",
        "entity": "North",
    }

    assert validate_evidence_reference(
        reference,
        evidence,
    ) is False


def test_reference_without_entity_is_valid():
    evidence = {
        "overall_sales": {
            "transactions": 1000,
            "units_sold": 5000,
            "revenue": 250000,
        }
    }

    reference = {
        "investigation": "overall_sales",
        "field": "revenue",
        "entity": None,
    }

    assert validate_evidence_reference(
        reference,
        evidence,
    ) is True


def test_invalid_reference_shape_is_rejected():
    evidence = {
        "regional_performance": [
            {
                "region": "South",
                "revenue": 120000,
            }
        ]
    }

    assert validate_evidence_reference(
        {
            "investigation": "regional_performance",
            "field": "revenue",
        },
        evidence,
    ) is False


def test_validate_supported_claim():
    evidence = {
        "regional_performance": [
            {
                "region": "South",
                "revenue": 120000,
            }
        ]
    }

    claim = {
        "id": "C1",
        "statement": (
            "South generated the highest "
            "regional revenue."
        ),
        "status": "supported",
        "evidence_refs": [
            {
                "investigation": (
                    "regional_performance"
                ),
                "field": "revenue",
                "entity": "South",
            }
        ],
    }

    validated = validate_claim(
        claim,
        evidence,
    )

    assert validated == {
        "id": "C1",
        "statement": (
            "South generated the highest "
            "regional revenue."
        ),
        "status": "supported",
        "evidence_refs": [
            {
                "investigation": (
                    "regional_performance"
                ),
                "field": "revenue",
                "entity": "South",
            }
        ],
        "traceability_status": "traceable",
    }


def test_claim_with_invalid_evidence_is_rejected():
    evidence = {
        "regional_performance": [
            {
                "region": "South",
                "revenue": 120000,
            }
        ]
    }

    claim = {
        "id": "C1",
        "statement": (
            "North generated the highest "
            "regional revenue."
        ),
        "status": "supported",
        "evidence_refs": [
            {
                "investigation": (
                    "regional_performance"
                ),
                "field": "revenue",
                "entity": "North",
            }
        ],
    }

    assert validate_claim(
        claim,
        evidence,
    ) is None


def test_invalid_claim_status_defaults_to_unverified():
    evidence = {
        "overall_sales": {
            "transactions": 1000,
            "units_sold": 5000,
            "revenue": 250000,
        }
    }

    claim = {
        "id": "C1",
        "statement": "Revenue was 250000.",
        "status": "made_up_status",
        "evidence_refs": [
            {
                "investigation": "overall_sales",
                "field": "revenue",
                "entity": None,
            }
        ],
    }

    validated = validate_claim(
        claim,
        evidence,
    )

    assert validated is not None
    assert validated["status"] == "unverified"
    assert (
        validated["traceability_status"]
        == "traceable"
    )


def test_claim_without_evidence_is_untraceable():
    evidence = {
        "overall_sales": {
            "transactions": 1000,
            "units_sold": 5000,
            "revenue": 250000,
        }
    }

    claim = {
        "id": "C1",
        "statement": "Revenue increased.",
        "status": "unverified",
        "evidence_refs": [],
    }

    validated = validate_claim(
        claim,
        evidence,
    )

    assert validated is not None
    assert (
        validated["traceability_status"]
        == "untraceable"
    )


def test_multiple_claims_are_filtered():
    evidence = {
        "regional_performance": [
            {
                "region": "South",
                "revenue": 120000,
            }
        ]
    }

    claims = [
        {
            "id": "C1",
            "statement": (
                "South generated the highest revenue."
            ),
            "status": "supported",
            "evidence_refs": [
                {
                    "investigation": (
                        "regional_performance"
                    ),
                    "field": "revenue",
                    "entity": "South",
                }
            ],
        },
        {
            "id": "C2",
            "statement": (
                "North generated the highest revenue."
            ),
            "status": "supported",
            "evidence_refs": [
                {
                    "investigation": (
                        "regional_performance"
                    ),
                    "field": "revenue",
                    "entity": "North",
                }
            ],
        },
    ]

    validated = validate_claims(
        claims,
        evidence,
    )

    assert len(validated) == 1
    assert validated[0]["id"] == "C1"