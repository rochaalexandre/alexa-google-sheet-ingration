import os
import sys
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SPREADSHEET_ID", "fake-id")
os.environ.setdefault("GOOGLE_CREDENTIALS", "{}")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lambda_function as lf


def make_handler_input(slots):
    handler_input = MagicMock()
    slot_mocks = {}
    for name, value in slots.items():
        slot_mock = MagicMock()
        slot_mock.value = value
        slot_mocks[name] = slot_mock
    handler_input.request_envelope.request.intent.slots = slot_mocks
    return handler_input


@patch("lambda_function.timestamp", return_value=("27/07/2026", "10:00"))
@patch("lambda_function.get_sheet")
def test_registrar_glicemia_grava_linha_correta(mock_get_sheet, mock_timestamp):
    mock_sheet = MagicMock()
    mock_get_sheet.return_value = mock_sheet

    handler_input = make_handler_input({"valor": "120"})
    handler = lf.RegistrarGlicemiaHandler()

    handler.handle(handler_input)

    mock_get_sheet.assert_called_once_with("Diabete")
    mock_sheet.append_row.assert_called_once_with(["27/07/2026", "10:00", "120"])


@patch("lambda_function.timestamp", return_value=("27/07/2026", "10:00"))
@patch("lambda_function.get_sheet")
def test_registrar_pressao_grava_linha_correta(mock_get_sheet, mock_timestamp):
    mock_sheet = MagicMock()
    mock_get_sheet.return_value = mock_sheet

    handler_input = make_handler_input({"sistolica": "130", "diastolica": "85"})
    handler = lf.RegistrarPressaoHandler()

    handler.handle(handler_input)

    mock_get_sheet.assert_called_once_with("Pressao")
    mock_sheet.append_row.assert_called_once_with(
        ["27/07/2026", "10:00", "130", "85"]
    )


@patch("lambda_function.get_sheet")
def test_registrar_glicemia_propaga_erro_se_sheet_falhar(mock_get_sheet):
    mock_get_sheet.side_effect = Exception("falha de conexao")

    handler_input = make_handler_input({"valor": "120"})
    handler = lf.RegistrarGlicemiaHandler()

    with pytest.raises(Exception):
        handler.handle(handler_input)
