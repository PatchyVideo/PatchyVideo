
class UserError(Exception) :
    def __init__(self, msg, aux = None) :
        self.msg = msg
        self.aux = aux

