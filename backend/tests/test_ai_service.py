from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.ai_service import analyze_complaint


def test_ai_output_is_validated_against_allowed_values():
    response = SimpleNamespace(
        text='{"category":"Plumbing","priority":"High","summary":"A tap is leaking.",'
        '"department":"Plumbing","explanation":"The report describes a leaking tap.",'
        '"review_flag":false}'
    )
    with patch("app.services.ai_service.genai.Client") as client:
        client.return_value.models.generate_content.return_value = response
        result = analyze_complaint("Leaking tap", "Water drips from a tap.", "Block A", "test-key")
    assert result["category"] == "Plumbing"
    assert result["priority"] == "High"


def test_ai_invalid_category_is_rejected():
    response = SimpleNamespace(
        text='{"category":"Made up","priority":"High","summary":"Summary",'
        '"department":"Plumbing","explanation":"Reason","review_flag":false}'
    )
    with patch("app.services.ai_service.genai.Client") as client:
        client.return_value.models.generate_content.return_value = response
        with pytest.raises(ValueError):
            analyze_complaint("Issue", "Description", "Block A", "test-key")
