import os
import shutil
import time
import logging

from visuanalytics.analytics.control.procedures.steps import Steps
from visuanalytics.analytics.util import resources

logger = logging.getLogger(__name__)


class Pipeline(object):
    """Enthält alle informationen zu einer Pipeline, und führt alle Steps aus.

    Benötigt beim Ersttellen eine id, und eine Instanz der Klasse :class:`Steps` bzw. einer Unterklasse von :class:`Steps`.
    Bei dem Aufruf von Start werden alle Steps der Reihe nach ausgeführt.
    """

    def __init__(self, pipeline_id: str, steps: Steps):
        self.__steps = steps
        self.__start_time = 0.0
        self.__end_time = 0.0
        self.__id = pipeline_id
        self.__current_step = -1

    @property
    def start_time(self):
        """float: Startzeit der Pipeline. Wird erst bei dem Aufruf von :func:`start` inizalisiert."""
        return self.__start_time

    @property
    def end_time(self):
        """float: Endzeit der Pipeline. Wird erst nach Beendigung der Pipeline inizalisiert."""
        return self.__end_time

    @property
    def id(self):
        """str: id der Pipeline."""
        return self.__id

    def progress(self):
        """Fortschritt der Pipeline.

        :return: Anzahl der schon ausgeführten schritte, Anzahl aller Schritte
        :rtype: int, int
        """
        return self.__current_step + 1, self.__steps.step_max + 1

    def current_step_name(self):
        """Gibt den Namen des aktuellen Schritts zurück.

        :return: Name des Aktuellen Schrittes.
        :rtype: str
        """
        return self.__steps.sequence[self.__current_step]["name"]

    def __setup(self):
        logger.info(f"Initializing Pipeline {self.id}...")
        os.mkdir(resources.get_temp_resource_path("", self.id))

    def __cleanup(self):
        # delete Directory
        logger.info("Cleaning up...")
        shutil.rmtree(resources.get_temp_resource_path("", self.id), ignore_errors=True)
        logger.info("Finished cleanup!")

    def start(self):
        """Führt alle Schritte die in der übergebenen Instanz der Klasse :class:`Steps` definiert sind aus.

        Initalisiertt zuerst einen Pipeline Ordner mit der Pipeline id, dieser kann dann im gesamten Pipeline zur
        zwichenspeicherung von dateien verwendet werden. Dieser wird nach Beendigung oder bei einem Fehler fall wieder gelöscht.

        Führt alle Schritte aus der übergebenen Steps instans, die in der Funktion :func:`sequence` difiniert sind,
        der reihnfolge nach aus. Mit der ausnahme von allen Steps mit der id < 0 und >= `step_max`.

        :return: Wenn ohne fehler ausgeführt `True`, sonst `False`
        :rtype: bool
        """
        self.__setup()
        self.__start_time = time.time()
        logger.info(f"Pipeline {self.id} started!")
        try:
            for idx in range(0, self.__steps.step_max):
                self.__current_step = idx
                logger.info(f"Next step: {self.current_step_name()}")
                self.__steps.sequence[idx]["call"](self.id)
                logger.info(f"Step finished: {self.current_step_name()}!")
                
            # Set state to ready
            self.__current_step = self.__steps.step_max
            self.__end_time = time.time()
            completion_time = round(self.__end_time - self.__start_time, 2)
            logger.info(f"Pipeline {self.id} finished in {completion_time}s")
            self.__cleanup()
            return True

        except Exception:
            # TODO(max)
            self.__current_step = -2
            logger.exception(f"An error occurred: ")
            logger.info(f"Pipeline {self.id} could not be finished.")
            self.__cleanup()
            return False
