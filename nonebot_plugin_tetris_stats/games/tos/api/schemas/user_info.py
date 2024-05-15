from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PeriodMatch(BaseModel):
    name: str
    teaid: str = Field(..., alias='teaId')
    rating: str
    rd: str
    start_time: datetime = Field(..., alias='startTime')
    end_time: datetime = Field(..., alias='endTime')
    win: str
    lose: str
    score: str


class UserDataTotalItem(BaseModel):
    time_map: str = Field(..., alias='timeMap')
    pieces_map: str = Field(..., alias='piecesMap')
    clear_lines_map: str = Field(..., alias='clearLinesMap')
    attacks_map: str = Field(..., alias='attacksMap')
    dig_map: str = Field(..., alias='digMap')
    send_map: str = Field(..., alias='sendMap')
    rise_map: str = Field(..., alias='riseMap')
    offset_map: str = Field(..., alias='offsetMap')
    receive_map: str = Field(..., alias='receiveMap')
    games_map: str = Field(..., alias='gamesMap')
    tetris_map: str = Field(..., alias='tetrisMap')
    combo_map: str = Field(..., alias='comboMap')
    tspin_map: str = Field(..., alias='tspinMap')
    b2b_map: str = Field(..., alias='b2bMap')
    perfect_clear_map: str = Field(..., alias='perfectClearMap')
    time_no_map: str = Field(..., alias='timeNoMap')
    pieces_no_map: str = Field(..., alias='piecesNoMap')
    clear_lines_no_map: str = Field(..., alias='clearLinesNoMap')
    attacks_no_map: str = Field(..., alias='attacksNoMap')
    dig_no_map: str = Field(..., alias='digNoMap')
    send_no_map: str = Field(..., alias='sendNoMap')
    rise_no_map: str = Field(..., alias='riseNoMap')
    offset_no_map: str = Field(..., alias='offsetNoMap')
    receive_no_map: str = Field(..., alias='receiveNoMap')
    games_no_map: str = Field(..., alias='gamesNoMap')
    tetris_no_map: str = Field(..., alias='tetrisNoMap')
    combo_no_map: str = Field(..., alias='comboNoMap')
    tspin_no_map: str = Field(..., alias='tspinNoMap')
    b2b_no_map: str = Field(..., alias='b2bNoMap')
    perfect_clear_no_map: str = Field(..., alias='perfectClearNoMap')


class Data(BaseModel):
    teaid: str = Field(..., alias='teaId')
    name: str
    total_exp: str = Field(..., alias='totalExp')
    ranking: str
    ranked_games: str = Field(..., alias='rankedGames')
    rating_now: str = Field(..., alias='ratingNow')
    rd_now: str = Field(..., alias='rdNow')
    vol_now: str = Field(..., alias='volNow')
    rating_last: str = Field(..., alias='ratingLast')
    rd_last: str = Field(..., alias='rdLast')
    vol_last: str = Field(..., alias='volLast')
    period_matches: list[PeriodMatch] = Field(..., alias='periodMatches')
    user_data_total: list[UserDataTotalItem] = Field(..., alias='userDataTotal')
    ranking_items: str = Field(..., alias='rankingItems')
    ranking_game_items: str = Field(..., alias='rankingGameItems')
    training_level: str = Field(..., alias='trainingLevel')
    training_wins: str = Field(..., alias='trainingWins')
    pb_sprint: str = Field(..., alias='PBSprint')
    pb_marathon: str = Field(..., alias='PBMarathon')
    pb_challenge: str = Field(..., alias='PBChallenge')
    register_date: datetime = Field(..., alias='registerDate')
    last_login_date: datetime = Field(..., alias='lastLoginDate')


class UserInfoSuccess(BaseModel):
    code: int
    success: Literal[True]
    data: Data


class FailedModel(BaseModel):
    code: int
    success: Literal[False]
    error: str


UserInfo = UserInfoSuccess | FailedModel
