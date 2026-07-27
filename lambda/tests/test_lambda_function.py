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
    mock_diabete = MagicMock()
    mock_criterios = MagicMock()
    mock_criterios.get_all_records.return_value = [
        {"min": "201", "max": "250", "dose": "2", "orientacao": "Aplicar 2 unidades de insulina regular"},
        {"min": "251", "max": "300", "dose": "3", "orientacao": "Aplicar 3 unidades de insulina regular"},
        {"min": "301", "max": "350", "dose": "4", "orientacao": "Aplicar 4 unidades de insulina regular"},
    ]

    def fake_get_sheet(nome):
        return {"Diabete": mock_diabete, "Criterios": mock_criterios}[nome]

    mock_get_sheet.side_effect = fake_get_sheet

    handler_input = make_handler_input({"valor": "220"})
    handler = lf.RegistrarGlicemiaHandler()

    handler.handle(handler_input)

    mock_diabete.append_row.assert_called_once_with(["27/07/2026", "10:00", "220"])
    fala = handler_input.response_builder.speak.call_args[0][0]
    assert "Aplicar 2 unidades de insulina regular" in fala


@patch("lambda_function.timestamp", return_value=("27/07/2026", "10:00"))
@patch("lambda_function.get_sheet")
def test_registrar_glicemia_sem_comentario_quando_dentro_do_normal(mock_get_sheet, mock_timestamp):
    mock_diabete = MagicMock()
    mock_criterios = MagicMock()
    mock_criterios.get_all_records.return_value = [
        {"min": "201", "max": "250", "dose": "2", "orientacao": "Aplicar 2 unidades de insulina regular"},
    ]

    def fake_get_sheet(nome):
        return {"Diabete": mock_diabete, "Criterios": mock_criterios}[nome]

    mock_get_sheet.side_effect = fake_get_sheet

    handler_input = make_handler_input({"valor": "180"})
    handler = lf.RegistrarGlicemiaHandler()

    handler.handle(handler_input)

    fala = handler_input.response_builder.speak.call_args[0][0]
    assert fala == "Registrei sua diabete em 180."


def test_buscar_criterio_encontra_faixa_correta():
    mock_sheet = MagicMock()
    mock_sheet.get_all_records.return_value = [
        {"min": "201", "max": "250", "dose": "2", "orientacao": "Aplicar 2 unidades"},
        {"min": "251", "max": "300", "dose": "3", "orientacao": "Aplicar 3 unidades"},
        {"min": "301", "max": "350", "dose": "4", "orientacao": "Aplicar 4 unidades"},
    ]

    with patch("lambda_function.get_sheet", return_value=mock_sheet):
        resultado = lf.buscar_criterio("280")

    assert resultado["orientacao"] == "Aplicar 3 unidades"


def test_buscar_criterio_retorna_none_fora_das_faixas():
    mock_sheet = MagicMock()
    mock_sheet.get_all_records.return_value = [
        {"min": "201", "max": "250", "dose": "2", "orientacao": "Aplicar 2 unidades"},
    ]

    with patch("lambda_function.get_sheet", return_value=mock_sheet):
        resultado = lf.buscar_criterio("180")

    assert resultado is None


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
