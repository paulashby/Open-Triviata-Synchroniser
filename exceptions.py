# User-defined exceptions
class Error(Exception):
    """Base class for other exceptions"""
    pass

class RequestError(Error):
 
    # Raised when API returns an unfixable error code.
    e_by_code = {
        2: "Invalid parameter passed to Open Trivia API",
        3: "Open Trivia API Session Token does not exist",
        5: "Open Trivia API returned an unknown error code"
    }

    def __init__(self, ecode):
        self.mssg = self.e_by_code[ecode]
        super().__init__(self.mssg)

        def __str__(self):
            return(self.mssg)

        @property
        def e_by_code(self):
            return self.e_by_code
        
 
