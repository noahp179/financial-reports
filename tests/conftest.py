from financial_reports.settings import load_settings


def settings():
    return load_settings("config/report_config.yaml")
