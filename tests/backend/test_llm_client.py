import pytest
import backend.core.llm_client as llm_client_module
from backend.core.llm_client import generate_explanation, classify_data_intent, PlainTextPrompt


class MockLLM:
    def __init__(self, return_text="Voici une explication claire."):
        self.return_text = return_text
        self.last_prompt = None

    def call(self, instruction):
        self.last_prompt = instruction.to_string()
        return self.return_text


def test_plain_text_prompt():
    prompt = PlainTextPrompt("test text")
    assert prompt.to_string() == "test text"
    assert str(prompt) == "test text"


def test_generate_explanation_with_call():
    mock_llm = MockLLM("Ce graphique montre une progression des ventes en 2024.")
    # Patch the module-level _current_llm — the variable that generate_explanation()
    # now reads directly, regardless of PandasAI config object shape.
    original = llm_client_module._current_llm
    try:
        llm_client_module._current_llm = mock_llm
        res = generate_explanation("Quel est le chiffre d'affaires ?", "bar", "CA 2024: 100k")
        assert res == "Ce graphique montre une progression des ventes en 2024."
        assert mock_llm.last_prompt is not None
        assert "CA 2024: 100k" in mock_llm.last_prompt
    finally:
        llm_client_module._current_llm = original


def test_classify_data_intent_with_call():
    original = llm_client_module._current_llm
    try:
        mock_llm = MockLLM("YES")
        llm_client_module._current_llm = mock_llm
        res = classify_data_intent("Montre moi les ventes par mois", ["ventes", "mois"])
        assert res is True
        assert mock_llm.last_prompt is not None
        assert "Montre moi les ventes par mois" in mock_llm.last_prompt

        mock_llm2 = MockLLM("NO")
        llm_client_module._current_llm = mock_llm2
        res = classify_data_intent("Bonjour comment ça va ?", ["ventes", "mois"])
        assert res is False
    finally:
        llm_client_module._current_llm = original
