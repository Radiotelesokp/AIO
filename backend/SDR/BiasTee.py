class BiasTee:
    def __init__(self, sdr, languageHelper):
        self.__sdr = sdr
        self.controlBiasTee("off")
        self.__languageHelper = languageHelper

    def getStatus(self):
        state = self.__sdr.readSetting("bias_tx")
        return "on" if state == "true" else "off"

    def controlBiasTee(self, action):
        if action.lower() == "on":
            self.__sdr.writeSetting("bias_tx", "true")
        elif action.lower() == "off":
            self.__sdr.writeSetting("bias_tx", "false")
        else:
            _ = self.__languageHelper.getTranslatedMessage("SDR")
            raise ValueError(f"{_("bias.tee.unsupported.action")} '{action}'")