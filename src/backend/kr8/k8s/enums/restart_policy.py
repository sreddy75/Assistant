from src.backend.kr8.utils.enum import ExtendedEnum


class RestartPolicy(str, ExtendedEnum):
    ALWAYS = "Always"
    ON_FAILURE = "OnFailure"
    NEVER = "Never"
