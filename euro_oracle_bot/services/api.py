import json
import time
import threading
import http.client
from logging import Logger

from models import Team, Match, Prediction
from models import get_group_by_api_stage_id, get_stage_by_api_stage_id, \
    get_match_status_by_api_value
from models import MATCH_STATUS_FINISHED
from .storage import StorageService
from .bot import BotService
from .utils import plural_points


class ApiService:
    def __init__(self,
                 storage: StorageService,
                 bot: BotService,
                 token: str,
                 logger: Logger):
        """
        :arg: storage - storage service
        :arg: bot - tg bot instance
        :arg: token - elenasport.io API token
        :arg: logger - logger object
        """
        self.storage = storage
        self.logger = logger
        self.api_token = token
        self.bot = bot

    def update(self):
        fixtures = self._get_all_fixtures()
        for fixture in fixtures:
            match = self.storage.get_match_by_api_id(fixture["id"])
            if match is None:
                match = Match()
                match.api_id = fixture["id"]
                match.group = get_group_by_api_stage_id(fixture["idStage"])
                match.stage = get_stage_by_api_stage_id(fixture["idStage"], fixture["round"])
                match.stadium = fixture["venueName"]

            if match.processed:
                continue

            match.team_home_id = self.process_team(fixture, "home")
            match.team_away_id = self.process_team(fixture, "away")
            match.datetime = fixture["date"]
            match.status = get_match_status_by_api_value(fixture["status"])
            match.home_goals_90 = fixture["team_home_90min_goals"]
            match.away_goals_90 = fixture["team_away_90min_goals"]
            match.home_goals_total = fixture["team_home_ET_goals"] + \
                                     fixture["team_home_90min_goals"]
            match.away_goals_total = fixture["team_away_ET_goals"] + \
                                     fixture["team_away_90min_goals"]
            if match.status == MATCH_STATUS_FINISHED and not match.processed:
                self.process_match_result(match)
            self.storage.create_or_update_match(match)

        threading.Timer(3600, self.update).start()

    def process_match_result(self, match: Match):
        predictions = self.storage.get_match_predictions(match.id)
        match_result = match.get_result()
        for pred in predictions:
            pred_result = pred.get_result()
            diff = abs(match.home_goals_90 - match.away_goals_90)
            if diff >= 3:
                if match.home_goals_90 == pred.home_goals and \
                        match.away_goals_90 == pred.away_goals:
                    pred.points = 5
                elif match_result == pred_result:
                    if diff == abs(pred.home_goals - pred.away_goals):
                        pred.points = 4
                    else:
                        pred.points = 1
            else:
                if match.home_goals_90 == pred.home_goals and \
                        match.away_goals_90 == pred.away_goals:
                    pred.points = 3
                elif match_result == pred_result:
                    if diff == abs(pred.home_goals - pred.away_goals):
                        pred.points = 2
                    else:
                        pred.points = 1

            if pred.user.notifications_on:
                self._notify_user(pred)

            if pred.points > 0:
                self.storage.create_or_update_prediction(pred)

        match.processed = True
        self.storage.create_or_update_match(match)

    def process_team(self, fixture: dict, prefix: str) -> int:
        team = self.storage.get_team_by_api_id(fixture["id" + prefix.title()])
        if team is not None:
            return team.id

        team = Team()
        team.api_id = fixture["id" + prefix.title()]
        team.title = fixture[prefix + "Name"]
        team.group = get_group_by_api_stage_id(fixture["idStage"])
        return self.storage.create_or_update_team(team)

    def _notify_user(self, pred: Prediction):
        match = pred.match
        msg = "Завершился один из матчей с вашим прогнозом!\n\n" \
              f"{match.str_score()}\n\n" \
              f"Ваш прогноз: {pred.home_goals} - {pred.away_goals}\n" \
              f"Вы заработали *{plural_points(pred.points)}*"
        self.bot.bot.send_message(pred.user.api_id, msg)

    def _get_all_fixtures(self) -> list:
        auth_token = self._get_auth_token(self.api_token)
        if auth_token == "":
            self.logger.error("auth token not set")
            return []

        all_fixtures = []
        conn = http.client.HTTPSConnection("football.elenasport.io")
        headers = {
            'Authorization': "Bearer " + auth_token,
        }
        page = 1
        while True:
            conn.request("GET", f"/v2/seasons/797/fixtures?page={page}", headers=headers)
            try:
                response = conn.getresponse()
            except http.client.ResponseNotReady as exception:
                self.logger.error("failed to send get request to elenasport.io: " + str(exception))
                break

            raw_data = response.read()
            data = json.loads(raw_data)

            if "data" not in data:
                self.logger.error("Missing data field in elenasport.io response: " + str(raw_data))
                break

            all_fixtures += data["data"]

            if not data["pagination"]["hasNextPage"]:
                break
            page += 1
            time.sleep(2)

        return all_fixtures

    def _get_auth_token(self, api_token: str) -> str:
        conn = http.client.HTTPSConnection("oauth2.elenasport.io")
        headers = {
            "Authorization": "Basic " + api_token,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = "grant_type=client_credentials"

        conn.request("POST", "/oauth2/token", payload, headers)
        try:
            response = conn.getresponse()
        except http.client.ResponseNotReady as exception:
            self.logger.error("failed to send auth request to elenasport.io: " + str(exception))
            return ""

        raw_data = response.read()
        data = json.loads(raw_data)

        if "error" in data:
            self.logger.error("get elenasport.io access token error: " + data["error"])
            return ""

        if "access_token" not in data:
            self.logger.error("missing access token field in elenasport.io response: " + str(data))
            return ""

        return data["access_token"]
