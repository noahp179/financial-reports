class FinancialReportsError(Exception):
    """Base exception for financial reports."""


class ValidationError(FinancialReportsError):
    code = "VALIDATION_ERROR"


class ProviderError(FinancialReportsError):
    code = "PROVIDER_ERROR"


class ModelStabilityError(FinancialReportsError):
    code = "MODEL_STABILITY_ERROR"


class InternalPipelineError(FinancialReportsError):
    code = "INTERNAL_PIPELINE_ERROR"
