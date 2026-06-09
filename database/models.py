from sqlalchemy import Column, Integer, String, BigInteger, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True)
    tag = Column(String)
    name = Column(String)
    tg_name = Column(String)
    role_name = Column(String)
    role_status = Column(String)
    reg_date = Column(String)

class Economy(Base):
    __tablename__ = 'economy'
    user_id = Column(BigInteger, primary_key=True)
    balance = Column(Integer, default=0)
    bs_tag = Column(String)
    last_daily = Column(String)

class ChatStat(Base):
    __tablename__ = 'chat_stats'
    user_id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, primary_key=True)
    messages_count = Column(Integer, default=0)
    last_message_date = Column(String)

class BaselineTrophy(Base):
    __tablename__ = 'baseline_trophies'
    tag = Column(String, primary_key=True)
    timestamp = Column(String, primary_key=True)
    trophies = Column(Integer)

class ChatLog(Base):
    __tablename__ = 'chat_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    user_id = Column(BigInteger)
    user_name = Column(String)
    text = Column(Text)
    timestamp = Column(String)

class ActiveGame(Base):
    __tablename__ = 'active_games'
    user_id = Column(BigInteger, primary_key=True)
    game_type = Column(String)
    state_json = Column(Text)