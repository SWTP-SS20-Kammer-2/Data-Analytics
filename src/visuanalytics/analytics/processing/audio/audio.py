"""
Modul, welches die grundlegenden Funktionen der Audioerzeugung beeinhaltet.
"""
import base64
import logging
import mimetypes

import gtts.tokenizer.symbols
from gtts import gTTS

from visuanalytics.analytics.apis.api import api_request
from visuanalytics.analytics.control.procedures.step_data import StepData
from visuanalytics.analytics.processing.audio.parts import part
from visuanalytics.analytics.util.step_errors import raise_step_error, AudioError, InvalidContentTypeError
from visuanalytics.analytics.util.step_pattern import data_get_pattern
from visuanalytics.analytics.util.type_utils import get_type_func, register_type_func
from visuanalytics.util import resources
from visuanalytics.util.config_manager import get_config

logger = logging.getLogger(__name__)

GENERATE_AUDIO_TYPES = {}
"""Ein Dictionary bestehend aus allen Generate-Audio-Typ-Methoden.  """


def _get_audio_config(values: dict, data: StepData):
    config = get_config()["audio"]
    custom_config = values["audio"].get("config", {})

    # if config in step-JSON is present, use that config
    config.update(custom_config)

    # init _audio with audio config
    data.insert_data("_audio|_conf", config, {})

    return config


@raise_step_error(AudioError)
def generate_audios(values: dict, data: StepData):
    config: dict = _get_audio_config(values, data)

    audio_func = get_type_func(config, GENERATE_AUDIO_TYPES)
    audio_func(values["audio"]["audios"], data, config)


def register_generate_audio(func):
    """Registriert die übergebene Funktion und versieht sie mit einem `"try/except"`-Block.
    Fügt eine Typ-Funktion dem Dictionary GENERATE_AUDIO_TYPES hinzu.

    :param func: die zu registrierende Funktion
    :return: Funktion mit try/except-Block
    """
    return register_type_func(GENERATE_AUDIO_TYPES, AudioError, func)


@register_generate_audio
def default(values: dict, data: StepData, config: dict):
    """Generiert eine Audiodatei mit der Python-Bibliothek gTTS.

    Wenn in der Konfiguration `sub_pairs` angegeben sind, werden diese den bisherigen `sub_pairs` hinzugefügt.
    `sub_pairs` sind bestimmte Wörter, die im Text ersetzt werden sollen.
    Beispiel: "z.B." soll vorgelesen werden als "zum Beispiel".

    :param values: Werte aus der JSON-Datei
    :param data: Daten aus der API
    :param config: Daten aus der Konfigurationsdatei
    :return:
    """
    for key in values:
        text = part.audio_parts(values[key]["parts"], data)

        sub_pairs = data.deep_format(config.get("sub_pairs", None), values=values)

        if sub_pairs:
            for key in sub_pairs:
                value = data.get_data(key, values)
                gtts.tokenizer.symbols.SUB_PAIRS.append((key, value))

        tts = gTTS(text, lang=data.format(config["lang"]))

        file_path = resources.new_temp_resource_path(data.data["_pipe_id"], data.format(config["format"]))
        tts.save(file_path)

        values[key] = file_path


@register_generate_audio
def custom(values: dict, data: StepData, config: dict):
    """Generiert eine Audiodatei mithilfe einer bestimmten TTS-API und Konfigurationen dafür.

    :param values: Werte aus der JSON-Datei
    :param data: Daten aus der API
    :param config: Daten aus der Konfigurationsdatei
    :return:
    """
    logger.info("Generate audio with custom audio config")

    _prepare_custom(config.get("prepare", None), data, config)

    for key in values:
        text = part.audio_parts(values[key]["parts"], data)

        data.data["_audio"]["text"] = text
        generate = config["generate"]
        generate["include_headers"] = True
        api_request(generate, data, "audio", "_audio|gen", True)

        values[key] = _save_audio(data.get_data("_audio|gen", values), data, config)


def _prepare_custom(values: dict, data: StepData, config: dict):
    if values is not None:
        api_request(values, data, "audio", "_audio|pre", True)


def _save_audio(response, data: StepData, config: dict):
    post_generate = config.get("post_generate", {})
    extension = data.format(post_generate["file_extension"]) if post_generate.get("file_extension",
                                                                                  None) is not None else None
    # if multiple requests were used, get only the request with the audio file
    if config["generate"]["type"].startswith("request_multiple"):
        audio_idx = data.format(config["generate"]["audio_idx"])
        response = response[audio_idx]

    content_type = response["headers"]["content-type"]
    audio = response["content"]

    # if content type is JSON, try to decode JSON string with base64
    if content_type.startswith("application/json"):
        # get audio string
        audio = data_get_pattern(data.format(post_generate["audio_key"]), audio)
        # decode Audio Key with base64
        audio = base64.b64decode(audio)
    elif extension is None:
        # check if content type is an audio type
        if not content_type.startswith("audio"):
            raise InvalidContentTypeError(None, content_type, "'audio/*'")

        # get file extention from mime type:
        extension = mimetypes.guess_all_extensions(content_type)[0].replace(".", "")

    audio_path = resources.new_temp_resource_path(data.data["_pipe_id"], extension)

    with open(audio_path, "wb") as fp:
        fp.write(audio)

    return audio_path
