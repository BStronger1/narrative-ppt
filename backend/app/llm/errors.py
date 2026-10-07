class LLMNotConfiguredError(RuntimeError):
    """未配置可用的 LLM 凭证。上层应提示用户配置，禁止伪造内容。"""


class LLMServiceError(RuntimeError):
    """只含安全公开提示，不带供应商响应或凭证。"""

    retryable = True


class LLMTimeoutError(LLMServiceError):
    pass


class LLMAccessError(LLMServiceError):
    retryable = False


class LLMRequestError(LLMServiceError):
    retryable = False


class InvalidModelOutputError(ValueError):
    """模型返回内容无法通过契约校验。"""


class InvalidOutlineOutputError(InvalidModelOutputError):
    def __init__(self, message: str, *, code: str = "outline_schema"):
        super().__init__(message)
        self.code = code


class InvalidSlideOutputError(InvalidModelOutputError):
    pass


class InvalidSlideEditOutputError(InvalidModelOutputError):
    pass
