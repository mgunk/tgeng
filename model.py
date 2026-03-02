import os
import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = sq.Column(sq.Integer, primary_key=True)
    chat_id = sq.Column(sq.BigInteger, unique=True, nullable=False)
    total_answers = sq.Column(sq.Integer, default=0)
    correct_answers = sq.Column(sq.Integer, default=0)


class CommonWord(Base):
    __tablename__ = "common_words"
    id = sq.Column(sq.Integer, primary_key=True)
    target_word = sq.Column(sq.String(100), nullable=False)
    translate_word = sq.Column(sq.String(100), nullable=False)


class UserWord(Base):
    __tablename__ = "user_words"
    id = sq.Column(sq.Integer, primary_key=True)

    # Внешние ключи (колонки)
    user_id = sq.Column(sq.Integer, sq.ForeignKey("users.id", ondelete="CASCADE"))
    word_id = sq.Column(sq.Integer, sq.ForeignKey("common_words.id", ondelete="CASCADE"))

    is_deleted = sq.Column(sq.Boolean, default=False)

    # Отношения (Объекты для удобства доступа в Python)
    # Называем их иначе, чтобы не было конфликта с именами колонок!
    user_rel = relationship(User, backref="u_words")
    word_rel = relationship(CommonWord, backref="w_users")


# Настройка БД
DSN = os.getenv("DSN")
engine = sq.create_engine(DSN)
Session = sessionmaker(bind=engine)


def create_db():
    # Удаляем и создаем заново, чтобы структура точно обновилась
    #Base.metadata.drop_all(engine) # Раскомментируй один раз, если ошибка останется
    Base.metadata.create_all(engine)
