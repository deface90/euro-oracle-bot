import os

from logging import Logger
from datetime import datetime

import telebot
from telebot.types import Update, ReplyKeyboardMarkup
from telebot import apihelper

from models import User, UserLog, Prediction, MatchFilter
from models import USER_STAGE_SIMPLE, USER_STAGE_ENTER_SCORE
from .utils import parse_group_name, parse_stage, parse_score, extract_arg

from .storage import StorageService

apihelper.ENABLE_MIDDLEWARE = True


class BotService:
    def __init__(self, storage: StorageService, token: str, logger: Logger):
        """
        :arg: storage - storage service
        :arg: token - Telegram bot token
        :arg: logger - logger object
        """
        self.storage = storage
        self.logger = logger
        self.bot = telebot.TeleBot(token, parse_mode="Markdown")

        self.bot.add_middleware_handler(self.user_middleware)
        self.bot.add_middleware_handler(self.log_middleware)
        self.bot.add_message_handler(self._build_handler_dict(self.all_matches,
                                                              commands=["matches"]))
        self.bot.add_message_handler(self._build_handler_dict(self.matches_today,
                                                              commands=["matchestoday"]))
        self.bot.add_message_handler(self._build_handler_dict(self.matches_group_select,
                                                              commands=["matchesgroup"]))
        self.bot.add_message_handler(self._build_handler_dict(self.matches_stage_select,
                                                              commands=["matchesstage"]))
        self.bot.add_message_handler(self._build_handler_dict(self.create_predict_next_match,
                                                              commands=["predict"]))
        self.bot.add_message_handler(self._build_handler_dict(self.create_predict_match_select,
                                                              commands=["predictmatch"]))
        self.bot.add_message_handler(self._build_handler_dict(self.get_user_predictions,
                                                              commands=["me"]))
        self.bot.add_message_handler(self._build_handler_dict(self.get_leaders,
                                                              commands=["leaders"]))
        self.bot.add_message_handler(self._build_handler_dict(self.start_message,
                                                              commands=["start"]))
        self.bot.add_message_handler(self._build_handler_dict(self.help_message,
                                                              commands=["help"]))
        self.bot.add_message_handler(self._build_handler_dict(self.unknown_message))

        self.bot.polling()

    def user_middleware(self, _, update: Update):
        try:
            user = self.storage.get_user_by_api_id(update.message.from_user.id)
        except AttributeError:
            return

        if user is None:
            user = User()
            user.api_id = update.message.from_user.id
            user.username = update.message.from_user.username
            user.full_name = update.message.from_user.full_name
            self.storage.create_or_update_user(user)

        update.message.user = user

    def log_middleware(self, _, update: Update):
        try:
            user = update.message.user
        except AttributeError:
            self.logger.error("Missing User object after user middleware")
            return

        log = UserLog(user.id, user.username, update.message.text)
        self.storage.create_or_update_userlog(log)
        update.message.log = log

    def all_matches(self, message):
        local_tz = os.getenv("TZ", "Asia/Yekaterinburg")
        matches = self.storage.find_matches(MatchFilter())
        msg = f"*Все матчи UEFA EURO 2020* (указано время {local_tz})\n\n"
        for match in matches:
            msg += f"{match}\n"

        self._send_response(message.chat.id, msg, message.log)

    def matches_today(self, message):
        filter_ = MatchFilter()
        filter_.datetime = datetime.utcnow()
        matches = self.storage.find_matches(filter_)

        msg = "*Матчи UEFA EURO 2020 за сегодня*\n\n"
        for match in matches:
            msg += f"{match}\n"

        self._send_response(message.chat.id, msg, message.log)

    def matches_group_select(self, message):
        group = extract_arg(message.text)
        if len(group) == 0:
            markup = ReplyKeyboardMarkup(one_time_keyboard=True)
            markup.add("A", "B", "C", "D", "E", "F")
            msg = self.bot.reply_to(message, "Выберите или укажите группу:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.matches_group)
            return

        message.text = group[0]
        self.matches_group(message)

    def matches_group(self, message):
        group = parse_group_name(message.text)
        if group == "":
            self.bot.send_message(message.chat.id, "Группа не найдена")
            return

        filter_ = MatchFilter()
        filter_.group = group
        matches = self.storage.find_matches(filter_)

        msg = f"*Матчи группы {group} на UEFA EURO 2020*\n\n"
        for match in matches:
            msg += f"{match}\n"

        self._send_response(message.chat.id, msg, message.log)

    def matches_stage_select(self, message):
        stage = extract_arg(message.text)
        if len(stage) == 0:
            markup = ReplyKeyboardMarkup(one_time_keyboard=True)
            markup.add("1 тур", "2 тур", "3 тур", "1/8 финала", "1/4 финала", "1/2 финала", "Финал")
            msg = self.bot.reply_to(message, "Выберите или укажите стадию:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.matches_stage)
            return

        message.text = stage[0]
        self.matches_stage(message)

    def matches_stage(self, message):
        stage = parse_stage(message.text)
        if stage == "":
            self.bot.send_message(message.chat.id, "Стадия не найдена")
            return

        filter_ = MatchFilter()
        filter_.stage = stage
        matches = self.storage.find_matches(filter_)

        msg = "*Матчи выбранной стадии на UEFA EURO 2020*\n\n"
        for match in matches:
            msg += f"{match}\n"

        self._send_response(message.chat.id, msg, message.log)

    def create_predict_next_match(self, message):
        match = self.storage.get_next_match_prediction(message.user.id)
        if match is None:
            self.bot.send_message(message.chat.id, "Следующий матч для прогнозирования не найден")
            return

        message.text = match.id
        self.create_predict_enter_score(message)

    def create_predict_match_select(self, message):
        match_id = extract_arg(message.text)
        if len(match_id) == 0:
            msg = self.bot.reply_to(message, "Укажите ID матча:")
            self.bot.register_next_step_handler(msg, self.create_predict_enter_score)
            return

        message.text = match_id[0]
        self.create_predict_enter_score(message)

    def create_predict_enter_score(self, message):
        try:
            if not message.text.isdigit():
                self._send_response(message.chat.id, "Алло, надо число набрать", message.log)
                return
        except AttributeError as _:
            pass

        match = self.storage.get_match(message.text)
        if match is None:
            self._send_response(message.chat.id, "Матч не найден", message.log)
            return

        user = message.user
        user.chat_stage = USER_STAGE_ENTER_SCORE
        user.chat_stage_payload = match.id
        self.storage.create_or_update_user(user)

        msg_text = f"Укажите счет матча\n{str(match)}\n\n" \
                   f"Поддерживаются различные варианты ('2 2', '3:3', '2 - 1' и т.д.)"
        msg = self._send_response(message.chat.id, msg_text, message.log)
        self.bot.register_next_step_handler(msg, self.create_predict)

    def create_predict(self, message):
        user = message.user
        if user.chat_stage != USER_STAGE_ENTER_SCORE:
            self._send_response(message.chat.id, "Матч не найден", message.log)
            return

        user = message.user
        user.chat_stage = USER_STAGE_SIMPLE
        self.storage.create_or_update_user(user)

        match = self.storage.get_match(message.user.chat_stage_payload)
        if match is None:
            self._send_response(message.chat.id, "Матч не найден", message.log)
            return

        scores = parse_score(message.text)
        if not scores[0]:
            self._send_response(message.chat.id, "Неверный формат счета", message.log)
            return

        prediction = self.storage.find_prediction(user.id, match.id)
        if prediction is None:
            prediction = Prediction()
            prediction.user_id = user.id
            prediction.match_id = match.id
            prediction.points = 0

        if prediction.match.datetime <= datetime.utcnow():
            self._send_response(message.chat.id, "Прогнозы на данный матч больше не принимаются",
                                message.log)
            return

        prediction.home_goals = scores[1]
        prediction.away_goals = scores[2]
        self.storage.create_or_update_prediction(prediction)

        msg = f"Прогноз принят\n{match.team_home.title} {scores[1]} - {scores[2]} " \
              f"{match.team_away.title}"
        self._send_response(message.chat.id, msg, message.log)

    def get_user_predictions(self, message):
        predictions = self.storage.get_user_predictions(message.user.id)
        msg = "*Ваши прогнозы на матчи UEFA EURO 2020*\n\n"
        total_points = 0
        for prediction in predictions:
            total_points += prediction.points
            msg += f"{prediction}\n"

        msg += f"\n*ВСЕГО ОЧКОВ: {total_points}*"
        self._send_response(message.chat.id, msg, message.log)

    def get_leaders(self, message):
        try:
            leaders, points = self.storage.get_user_leaders()
        except ValueError:
            self._send_response(message.chat.id, "*На данный момент прогнозы отсутствуют*", message.log)
            return

        msg = "*Лидеры прогнозов на матчи UEFA EURO 2020*\n\n"
        i = 1
        for leader, point in leaders, points:
            msg += f"{i}. _{leader}_: *{point}*\n"
            i += 1

        self._send_response(message.chat.id, msg, message.log)

    def start_message(self, message):
        self._send_response(message.chat.id, """
Бот для игры в прогнозы на матчи UEFA EURO 2020 приветствует Вас!
        
Для просмотра доступных комманд, начните набирать "/" или введите "/help"
        """, message.log)

    def help_message(self, message):
        self._send_response(message.chat.id, """
Доступные команды:

/matches - список всех матчей турнира
/matchestoday - матчи сегодняшнего игрового дня
/matchesgroup - список матчей группы
/matchesstage - список матчей стадии турнира
/predict - прогнозировать следующий матч
/predictmatch - создание или редактирование прогноза на любой матч
/me - ваши результаты и прогнозы
/leaders - текущая таблица лидеров (ТОП-30)
/help - это сообщение

Подсчет очков осуществляется по следующим правилам:
- за угаданный точный счет матча при крупной победе одной из команд (с разницей в 3 и более мяча) - *5 очков*
- за угаданную разницу и победителя матча крупной победе одной из команд - *4 очка*
- за угаданный точный счет матча - *3 очка*
- за угаданную разницу и победителя матча (или ничейного исхода) - *2 очка*
- за угаданного победителя матча - *1 очко*

*В плей-офф результаты приниматются на результат основного времени матча!*
""", message.log)

    def unknown_message(self, message):
        self._send_response(message.chat.id, """
Бот Вас не понял :( Для просмотра доступных комманд, начнете набирать "/" или введите "/help"
        """, message.log)

    def _send_response(self, chat_id: int, msg: str, log: UserLog):
        try:
            message = self.bot.send_message(chat_id, msg)
        except apihelper.ApiException:
            return None
        log.response = msg[0:255]
        self.storage.create_or_update_userlog(log)
        return message

    @staticmethod
    def _build_handler_dict(handler, **filters):
        filters["content_types"] = ["text"]
        return {
            'function': handler,
            'filters': filters
        }
