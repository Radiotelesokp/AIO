import os
from babel.support import Translations

class LanguageHelper:
    __language: str
    __defaultLanguage: str

    def __init__(self, language: str, defaultLanguage: str):
        self.__language = language
        self.__defaultLanguage = defaultLanguage
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.LOCALES_DIR = os.path.join(BASE_DIR, "AIO/backend/locales")
        self.__supportedLanguages = ["en", "pl"]

    def getLanguage(self) -> str:
        return self.__language

    def getDefaultLanguage(self) -> str:
        return self.__defaultLanguage

    def changeLanguage(self, language: str):
        if language not in self.__supportedLanguages:
            self.__language = language
        else :
            raise ValueError("Language must be one of: " + ", ".join(self.__supportedLanguages))

    def __getTranslations(self, module):
        """Load compiled .mo translation for a given language"""
        module_dir = os.path.join(self.LOCALES_DIR, module)
        try:
            return Translations.load(module_dir, [self.__language])
        except Exception:
            return Translations.load(module_dir, [self.__defaultLanguage])

    def getTranslatedMessage(self, module: str):
        """Shortcut to get gettext function"""
        return self.__getTranslations(module).gettext
