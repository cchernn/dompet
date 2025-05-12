class InvalidParamsException(Exception):
    def __init__(self, ex: Exception):
        super().__init__(ex)
        message = f"{self.__class__.__name__}: {type(ex).__name__}-{str(ex)}"
        print(message)
        self.message = message

class InvalidFunctionException(Exception):
    def __init__(self, ex: Exception):
        super().__init__(ex)
        message = f"{self.__class__.__name__}: {type(ex).__name__}-{str(ex)}"
        print(message)
        self.message = message

class DBConnectionException(Exception):
    def __init__(self, ex: Exception):
        super().__init__(ex)
        message = f"{self.__class__.__name__}: {type(ex).__name__}-{str(ex)}"
        print(message)
        self.message = message

class DBOperationException(Exception):
    def __init__(self, ex: Exception):
        super().__init__(ex)
        message = f"{self.__class__.__name__}: {type(ex).__name__}-{str(ex)}"
        print(message)
        self.message = message