import json
import os
import datetime
import gspread
from google.oauth2.service_account import Credentials

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
)
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_sheet(worksheet_name):
    creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(worksheet_name)


def timestamp():
    now = datetime.datetime.now()
    return now.strftime("%d/%m/%Y"), now.strftime("%H:%M")


def buscar_criterio(valor):
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
        speak_output = "Pode registrar sua diabete ou sua pressão."
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
        valor = slots["valor"].value

        data, hora = timestamp()
        sheet = get_sheet("Diabete")
        sheet.append_row([data, hora, valor])

        criterio = buscar_criterio(valor)
        if criterio is None:
            speak_output = f"Registrei sua diabete em {valor}."
        else:
            orientacao = criterio["orientacao"]
            speak_output = f"Registrei sua diabete em {valor}. {orientacao}."

        return handler_input.response_builder.speak(speak_output).response


class RegistrarPressaoHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("RegistrarPressao")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        sistolica = slots["sistolica"].value
        diastolica = slots["diastolica"].value

        data, hora = timestamp()
        sheet = get_sheet("Pressao")
        sheet.append_row([data, hora, sistolica, diastolica])

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
        speak_output = "Desculpa, não consegui registrar. Pode repetir?"
        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(RegistrarGlicemiaHandler())
sb.add_request_handler(RegistrarPressaoHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
