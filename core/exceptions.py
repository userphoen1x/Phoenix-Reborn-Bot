class BotBaseException(Exception):
    pass

class UserNotRegisteredError(BotBaseException):
    def __init__(self, message="❌ Вы не зарегистрированы! Отправьте свой тег боту в ЛС."):
        super().__init__(message)

class WorkCooldownError(BotBaseException):
    def __init__(self, hours: int, minutes: int):
        self.hours = hours
        self.minutes = minutes
        super().__init__(f"⏳ Ожидание... Вы сможете работать через <b>{hours}ч {minutes}м</b>.")

class NotEnoughMoneyError(BotBaseException):
    def __init__(self, message="❌ Недостаточно средств!"):
        super().__init__(message)

class AccessDeniedError(BotBaseException):
    def __init__(self, message="❌ У вас нет прав для выполнения этой команды."):
        super().__init__(message)