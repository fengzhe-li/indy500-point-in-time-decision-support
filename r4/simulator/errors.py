class R4ConfigurationError(RuntimeError):
    """Raised when a simulator component or parameter has not been configured."""


class NotConfiguredError(R4ConfigurationError):
    def __init__(self, component: str):
        super().__init__(
            f"{component} is NOT_CONFIGURED. Supply a research-approved implementation "
            "and explicit parameter values before running simulations."
        )
        self.component = component
