import pytz
import os

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# pylint: disable=no-name-in-module
from pydantic import BaseModel

Base = declarative_base()

STAGE_1 = 10
STAGE_2 = 20
STAGE_3 = 30
STAGE_18 = 40
STAGE_14 = 50
STAGE_12 = 60
STAGE_FINAL = 70

MATCH_STATUS_NOT_STARTED = 10
MATCH_STATUS_IN_PROGRESS = 20
MATCH_STATUS_FINISHED = 30

MATCH_RESULT_HOME_WIN = 10
MATCH_RESULT_AWAY_WIN = 20
MATCH_RESUST_DRAW = 0

USER_STAGE_SIMPLE = 0
USER_STAGE_ENTER_SCORE = 10


# pylint: disable=too-few-public-methods
class User(Base):
    __tablename__ = "user"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    api_id = Column("api_id", Integer, index=True, nullable=False)
    username = Column("username", String, nullable=True)
    full_name = Column("full_name", String, nullable=True)
    chat_stage = Column("chat_stage", Integer, nullable=True)
    chat_stage_payload = Column("chat_stage_payload", String, nullable=True)
    created = Column("created", DateTime, nullable=True)

    def __str__(self) -> str:
        if self.full_name != "":
            return f"{self.full_name} ({self.username})"

        return self.username


# pylint: disable=too-few-public-methods
class UserLog(Base):
    __tablename__ = "userlog"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, index=True)
    username = Column("username", String, nullable=True)
    request = Column("request", String, nullable=True)
    response = Column("response", String, nullable=True)
    created = Column("created", DateTime, nullable=True)

    def __init__(self, user_id: int, username: str, request: str):
        self.user_id = user_id
        self.username = username
        self.request = request


# pylint: disable=too-few-public-methods
class Team(Base):
    __tablename__ = "team"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    api_id = Column("api_id", Integer, nullable=False)
    title = Column("title", String, nullable=False)
    rus_title = Column("rus_title", String, nullable=True)
    alias = Column("alias", String, nullable=True)
    flag = Column("flag", String, nullable=True)
    group = Column("group", String, nullable=True)
    active = Column("active", Boolean, nullable=True)


# pylint: disable=too-few-public-methods
class Match(Base):
    __tablename__ = "match"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    api_id = Column("api_id", Integer, nullable=False)
    datetime = Column("datetime", DateTime, nullable=False)
    stage = Column("stage", Integer, nullable=False)
    group = Column("group", String, nullable=False, index=True)
    stadium = Column("stadium", String, nullable=True)
    team_home_id = Column("team_home_id", Integer, ForeignKey(Team.id, ondelete="CASCADE"),
                          index=True)
    team_away_id = Column("team_away_id", Integer, ForeignKey(Team.id, ondelete="CASCADE"),
                          index=True)
    team_home: Team = relationship("Team", foreign_keys=[team_home_id])
    team_away: Team = relationship("Team", foreign_keys=[team_away_id])
    home_goals_90 = Column("home_goals_90", Integer, nullable=True)
    away_goals_90 = Column("away_goals_90", Integer, nullable=True)
    home_goals_total = Column("home_goals_total", Integer, nullable=True)
    away_goals_total = Column("away_goals_total", Integer, nullable=True)
    status = Column("status", Integer, nullable=True)
    processed = Column("processed", Boolean, nullable=True)
    updated = Column("updated", DateTime, nullable=True)
    created = Column("created", DateTime, nullable=True)

    def __str__(self):
        tz = pytz.timezone(os.getenv("TZ", "Asia/Yekaterinburg"))
        match_dt = self.datetime.replace(tzinfo=pytz.utc).astimezone(tz)
        match_str = f"*ID {self.id}*. {match_dt.strftime('%d.%m.%Y %H:%M')} "
        if self.stage < STAGE_18:
            match_str += f"_Группа {self.group}_"
        elif self.stage == STAGE_18:
            match_str += "_1/8 финала_"
        elif self.stage == STAGE_14:
            match_str += "_1/4 финала_"
        elif self.stage == STAGE_12:
            match_str += "_1/2 финала_"
        elif self.stage == STAGE_FINAL:
            match_str += "_Финал_"

        if self.status == MATCH_STATUS_NOT_STARTED:
            match_str += f" : {self.team_home.title} - {self.team_away.title}" \
                         f" *(не начался)*"
        elif self.status == MATCH_STATUS_FINISHED:
            match_str += f" : *{self.id}*: {self.team_home.title}  *{self.home_goals_total}*" \
                         f" - *{self.away_goals_total}*  {self.team_away.title}"

        return match_str

    def get_result(self) -> int:
        return get_match_result(self.home_goals_90, self.away_goals_90)


# pylint: disable=too-few-public-methods
class Prediction(Base):
    __tablename__ = "prediction"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    user_id = Column("user_id", Integer, ForeignKey(User.id, ondelete="CASCADE"), index=True)
    user: User = relationship("User")
    match_id = Column("match_id", Integer, ForeignKey(Match.id, ondelete="CASCADE"), index=True)
    match: Match = relationship("Match")
    home_goals = Column("home_goals", Integer, nullable=True)
    away_goals = Column("away_goals", Integer, nullable=True)
    points = Column("points", Integer, nullable=True)
    created = Column("created", DateTime, nullable=True)
    updated = Column("updated", DateTime, nullable=True)

    def __str__(self):
        match = self.match
        pred_str = str(match) + "\n"

        pred_str += f"*Ваш прогноз: _{self.home_goals} - {self.away_goals}_*"
        if match.status == MATCH_STATUS_FINISHED:
            pred_str += f" (очков: *{self.points}*"

        return pred_str

    def get_result(self) -> int:
        return get_match_result(self.home_goals, self.away_goals)


class MatchFilter(BaseModel):
    group: Optional[str] = None
    datetime: Optional[datetime] = None
    team_id: Optional[int] = None
    stage: Optional[int] = None


def get_group_by_api_stage_id(stage_id: int) -> str:
    # see https://football.elenasport.io/v2/seasons/797/stages
    return {
        2512: "A",
        2513: "B",
        2514: "D",
        2515: "C",
        2516: "E",
        2517: "F"
    }.get(stage_id, "")


def get_stage_by_api_stage_id(stage_id: int, round_: int) -> int:
    # see https://football.elenasport.io/v2/seasons/797/stages
    stages = {
        2518: STAGE_18,
        2519: STAGE_14,
        2520: STAGE_12,
        2521: STAGE_FINAL
    }
    if stage_id in stages:
        return stages[stage_id]

    rounds = {
        1: STAGE_1,
        2: STAGE_2,
        3: STAGE_3
    }
    if round_ in rounds:
        return rounds[round_]

    return 0


def get_match_status_by_api_value(status: str) -> int:
    # see https://elenasport.io/doc/football-api/allfixtures
    return {
        "in progress": MATCH_STATUS_NOT_STARTED,
        "finished": MATCH_STATUS_FINISHED,
    }.get(status, MATCH_STATUS_NOT_STARTED)


def get_match_result(home_goals: int, away_goals: int) -> int:
    if home_goals > away_goals:
        return MATCH_RESULT_HOME_WIN
    if home_goals < away_goals:
        return MATCH_RESULT_AWAY_WIN

    return MATCH_RESUST_DRAW
