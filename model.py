import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class CommonWord(Base):
    __tablename__ = "common_words"
    id = sq.Column(sq.Integer, primary_key=True)
    word = sq.Column(sq.String(length = 40), unique=True, nullable=False)
    translate = sq.Column(sq.String(length = 40), nullable=False)


class UserWord(Base):
    __tablename__ = "user_words"
    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.BigInteger, nullable=False)
    word = sq.Column(sq.String(length = 40), nullable=False)
    translate = sq.Column(sq.String(length = 40), nullable=False)
    is_deleted = sq.Column(sq.Boolean, default=False)

    __table_args__ = (sq.UniqueConstraint('user_id', 'word'),)


DSN = ''
engine = sq.create_engine(
    DSN,
    client_encoding='utf8'
)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

# Функция для получения всех доступных слов для пользователя
def get_all_words_for_user(user_id):
    session = Session()
    # Берём общие слова + слова пользователя, исключаем удалённые
    common = session.query(CommonWord.word, CommonWord.translate).all()
    user = session.query(UserWord.word, UserWord.translate)\
        .filter(UserWord.user_id == user_id, UserWord.is_deleted == False).all()

    deleted = [w[0] for w in session.query(UserWord.word).filter(UserWord.user_id == user_id, UserWord.is_deleted == True).all()]

    all_words = []
    for w in common:
        if w.word not in deleted:
            all_words.append(w)
    all_words.extend(user)

    session.close()
    return all_words
