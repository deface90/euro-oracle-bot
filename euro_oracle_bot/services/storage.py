from logging import Logger
from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload
from sqlalchemy import asc, desc, func

from models import User, UserLog, Match, Team, Prediction, MatchFilter
from db import Db


class StorageService:
    def __init__(self, db_service: Db, logger: Logger):
        """
        :arg: db - db service
        :arg: logger - logger object
        """
        self.db_service = db_service
        self.logger = logger

    def get_user(self, id_: int) -> User:
        with self.db_service.session_scope() as sess:
            query = sess.query(User).filter(User.id == id_)
            user = query.one_or_none()

        return user

    def get_user_by_api_id(self, api_id: int) -> User:
        with self.db_service.session_scope() as sess:
            query = sess.query(User).filter(User.api_id == api_id)
            user = query.one_or_none()

        return user

    def create_or_update_user(self, user: User) -> int:
        with self.db_service.session_scope() as sess:
            user.created = datetime.utcnow()
            sess.add(user)

        return user.id

    def get_user_leaders(self, limit: int = 30) -> list[User, int]:
        with self.db_service.session_scope() as sess:
            rows = sess.query(
                User,
                func.sum(Prediction.points).label("points")
            ).join(Prediction).group_by(User.id).order_by(desc("points")).limit(limit)

        return rows

    def create_or_update_userlog(self, log: UserLog):
        with self.db_service.session_scope() as sess:
            log.created = datetime.utcnow()
            sess.add(log)

    def get_all_teams(self):
        with self.db_service.session_scope() as sess:
            teams = sess.query(Team).all()

        return teams

    def get_team(self, id_: int) -> Team:
        with self.db_service.session_scope() as sess:
            query = sess.query(Team).filter(Team.id == id_)
            match = query.one_or_none()

        return match

    def get_team_by_api_id(self, api_id: int) -> Team:
        with self.db_service.session_scope() as sess:
            query = sess.query(Team).filter(Team.api_id == api_id)
            team = query.one_or_none()

        return team

    def create_or_update_team(self, team: Team) -> int:
        with self.db_service.session_scope() as sess:
            sess.add(team)

        return team.id

    def find_matches(self, filter_: MatchFilter) -> list[Match]:
        with self.db_service.session_scope() as sess:
            query = sess.query(Match)
            if filter_.group:
                query = query.filter(Match.group == filter_.group)
            if filter_.stage:
                query = query.filter(Match.stage == filter_.stage)
            if filter_.team_id:
                query = query.filter(
                    Match.team_home_id == filter_.team_id or
                    Match.team_away_id == filter_.team_id
                )
            if filter_.datetime:
                date = filter_.datetime.date()
                from_date = datetime(date.year, date.month, date.day)
                to_date = from_date + timedelta(1)
                query = query.filter(from_date <= Match.datetime)
                query = query.filter(to_date >= Match.datetime)

            query = query.order_by(asc(Match.datetime))

            matches = query.options(
                joinedload(Match.team_home), joinedload(Match.team_away)
            ).all()

        return matches

    def get_match(self, id_: int) -> Match:
        with self.db_service.session_scope() as sess:
            query = sess.query(Match).filter(Match.id == id_)
            match = query.options(
                joinedload(Match.team_home), joinedload(Match.team_away)
            ).one_or_none()

        return match

    def get_match_by_api_id(self, api_id: int) -> Match:
        with self.db_service.session_scope() as sess:
            query = sess.query(Match).filter(Match.api_id == api_id)
            match = query.one_or_none()

        return match

    def create_or_update_match(self, match: Match) -> int:
        with self.db_service.session_scope() as sess:
            if match.id == 0:
                match.created = datetime.utcnow()
            match.updated = datetime.utcnow()
            sess.add(match)

        return match.id

    def get_next_match_prediction(self, user_id: int):
        with self.db_service.session_scope() as sess:
            subquery = sess.query(Prediction).filter(Prediction.user_id == user_id)
            subquery = subquery.with_entities(Prediction.match_id)

            query = sess.query(Match).order_by(asc(Match.datetime))
            query = query.filter(Match.id.not_in(subquery))
            query = query.filter(Match.datetime > datetime.utcnow())
            return query.first()

    def find_prediction(self, user_id: int, match_id: int) -> Prediction:
        with self.db_service.session_scope() as sess:
            query = sess.query(Prediction)
            query = query.filter(Prediction.match_id == match_id)
            query = query.filter(Prediction.user_id == user_id)
            prediction = query.one_or_none()

        return prediction

    def get_user_predictions(self, user_id: int) -> list[Prediction]:
        with self.db_service.session_scope() as sess:
            query = sess.query(Prediction).join(Match)
            query = query.filter(Prediction.user_id == user_id)
            predictions = query.options(
                joinedload(Prediction.match).joinedload(Match.team_home),
                joinedload(Prediction.match).joinedload(Match.team_away),
            ).all()

        return predictions

    def get_match_predictions(self, match_id: int) -> list[Prediction]:
        with self.db_service.session_scope() as sess:
            query = sess.query(Prediction).join(Match)
            query = query.filter(Prediction.match_id == match_id)
            predictions = query.all()

        return predictions

    def create_or_update_prediction(self, prediction: Prediction) -> int:
        with self.db_service.session_scope() as sess:
            if prediction.id == 0:
                prediction.created = datetime.utcnow()
            prediction.updated = datetime.utcnow()
            sess.add(prediction)

        return prediction.id
