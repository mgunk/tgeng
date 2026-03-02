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
        if 'translate_word' in fields:
            translate_word = fields['translate_word']
        else:
            translate_word = fields['translate_word']

        target_word = fields['target_word']

        print(f'Импортирую: {target_word} -> {translate_word}')

        session.add(CommonWord(
            target_word=target_word,
            translate_word=translate_word
        ))

session.commit()