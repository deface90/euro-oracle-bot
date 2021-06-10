import re
import models


def extract_arg(arg):
    return arg.split()[1:]


def parse_group_name(msg: str) -> str:
    if msg.upper() in ["A", "B", "C", "D", "E", "F"]:
        return msg.upper()

    return ""


def parse_stage(msg: str) -> str:
    msg = msg.split()[0].upper().replace("\\", "/").replace("ФИНАЛ", "FINAL")
    stages = {
        "1": models.STAGE_1,
        "2": models.STAGE_2,
        "3": models.STAGE_3,
        "1/8": models.STAGE_18,
        "1/4": models.STAGE_14,
        "1/2": models.STAGE_12,
        "FINAL": models.STAGE_FINAL
    }

    if msg in stages:
        return stages[msg]

    return ""


def parse_score(msg: str) -> tuple[bool, int, int]:
    regex = re.compile(r'\d+(?:\d+)?')
    numbers = regex.findall(msg)

    if len(numbers) != 2:
        return False, 0, 0

    return True, numbers[0], numbers[1]


def plural_points(points):
    point_plurals = ['очко', 'очка', 'очков']

    if points % 10 == 1 and points % 100 != 11:
        idx = 0
    elif 2 <= points % 10 <= 4 and (points % 100 < 10 or points % 100 >= 20):
        idx = 1
    else:
        idx = 2

    return str(points) + ' ' + point_plurals[idx]
