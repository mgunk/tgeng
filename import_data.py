import json
from model import Session, CommonWord

session = Session()

# Очищаем таблицу если там уже что то было
session.query(CommonWord).delete()

with open('fixtures/tests_data.json', 'r', encoding='utf-8') as fd:
    data = json.load(fd)

for record in data:
    if record.get('model') == 'words':
        fields = record.get('fields', {})

        # Исправляем опечатку в первом поле
        if 'correct_translate' in fields:
            translate = fields['correct_translate']
        else:
            translate = fields['translate']

        word = fields['word']

        print(f'Импортирую: {word} -> {translate}')

        session.add(CommonWord(
            word=word,
            translate=translate
        ))

session.commit()
session.close()