import datetime
import json
import logging
import os

import gspread
import pytz
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
    AbstractRequestInterceptor,
    AbstractResponseInterceptor,
)
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_intent_name, is_request_type

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TIMEZONE_PADRAO = "America/Sao_Paulo"

try:
    from config import SPREADSHEET_ID, GOOGLE_CREDENTIALS
except ImportError:
    SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
    GOOGLE_CREDENTIALS = json.loads(os.environ["GOOGLE_CREDENTIALS"])

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


_spreadsheet = None


def _get_spreadsheet():
    global _spreadsheet
    if _spreadsheet is None:
        logger.debug("Autenticando no Google Sheets (login unico por execucao da lambda)")
        gc = gspread.service_account_from_dict(GOOGLE_CREDENTIALS)
        _spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    return _spreadsheet


def get_sheet(worksheet_name):
    logger.debug("Abrindo a aba '%s'", worksheet_name)
    return _get_spreadsheet().worksheet(worksheet_name)


def timestamp(timezone_name=TIMEZONE_PADRAO):
    tz = pytz.timezone(timezone_name)
    now = datetime.datetime.now(pytz.utc).astimezone(tz)
    data, hora = now.strftime("%d/%m/%Y"), now.strftime("%H:%M")
    logger.debug("Hora calculada para timezone=%s: data=%s hora=%s", timezone_name, data, hora)
    return data, hora


def buscar_criterio(valor):
    logger.debug("Buscando criterio para valor=%s", valor)
    sheet = get_sheet("Criterios")
    linhas = sheet.get_all_records()

    valor_numerico = float(valor)
    for linha in linhas:
        minimo = float(linha["min"])
        maximo = float(linha["max"])
        if minimo <= valor_numerico <= maximo:
            return linha
    return None


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = "O que você gostaria de registrar sua diabete ou sua pressão."
        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class RegistrarGlicemiaHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("RegistrarGlicemia")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        glicemia = slots["glicemia"].value
        logger.debug("RegistrarGlicemia recebido: glicemia=%s", glicemia)

        data, hora = timestamp()
        sheet = get_sheet("Diabete")
        sheet.append_row([data, hora, glicemia])
        logger.debug("Linha gravada na aba Diabete: %s", [data, hora, glicemia])

        criterio = buscar_criterio(glicemia)
        if criterio is None:
            speak_output = f"Registrei sua diabete em {glicemia}."
        else:
            orientacao = criterio["orientacao"]
            speak_output = f"Registrei sua diabete em {glicemia}. {orientacao}."

        return handler_input.response_builder.speak(speak_output).response


class RegistrarPressaoHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("RegistrarPressao")(handler_input)

    def handle(self, handler_input):
        request = handler_input.request_envelope.request

        slots = request.intent.slots
        sistolica = slots["sistolica"].value
        diastolica = slots["diastolica"].value
        logger.info("RegistrarPressao recebido: sistolica=%s diastolica=%s", sistolica, diastolica)

        data, hora = timestamp()
        sheet = get_sheet("Pressao")
        sheet.append_row([data, hora, sistolica, diastolica])
        logger.debug("Linha gravada na aba Pressao: %s", [data, hora, sistolica, diastolica])

        speak_output = f"Registrei sua pressão em {sistolica} por {diastolica}."
        return handler_input.response_builder.speak(speak_output).response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "Diga, por exemplo: registrar diabete 120. Ou: registrar pressão 12 por 8."
        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "Não entendi. Você pode dizer, por exemplo: registrar diabete 120, ou registrar pressão."
        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name(
            "AMAZON.StopIntent"
        )(handler_input)

    def handle(self, handler_input):
        speak_output = "Até mais."
        return handler_input.response_builder.speak(speak_output).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error("Erro nao tratado: %s", exception, exc_info=True)
        speak_output = "Desculpa, não consegui registrar. Pode repetir?"
        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class RequestLogger(AbstractRequestInterceptor):
    def process(self, handler_input):
        logger.info("Request recebido: %s", handler_input.request_envelope.request)


class ResponseLogger(AbstractResponseInterceptor):
    def process(self, handler_input, response):
        logger.info("Response enviado: %s", response)


sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(RegistrarGlicemiaHandler())
sb.add_request_handler(RegistrarPressaoHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())
sb.add_global_request_interceptor(RequestLogger())
# sb.add_global_response_interceptor(ResponseLogger())  # habilitar quando precisar depurar responses

lambda_handler = sb.lambda_handler()
