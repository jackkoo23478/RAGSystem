class DocumentNotFoundError(Exception):
    pass

class EmptyDocumentError(Exception):
    pass


class SuspiciousDocumentError(Exception):
    def __init__(self, signals):
        super().__init__("Document contains text that looks like instructions to an AI model.")
        self.signals = signals
