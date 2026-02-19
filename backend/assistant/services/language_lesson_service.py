from typing import Dict, List

_SUPPORTED_LANGUAGES = {
    'en': 'English',
    'fr': 'French',
    'de': 'German',
}

_LEVELS = {'beginner', 'intermediate', 'advanced'}


def _validate_language(language: str) -> str:
    lang = (language or '').strip().lower()
    if lang not in _SUPPORTED_LANGUAGES:
        raise ValueError('Unsupported language. Use en, fr or de.')
    return lang


def _validate_level(level: str) -> str:
    lv = (level or '').strip().lower()
    if lv not in _LEVELS:
        raise ValueError('Unsupported level. Use beginner, intermediate or advanced.')
    return lv


def build_language_lesson(language: str, level: str, topic: str) -> Dict:
    """
    Build a compact lesson plan and starter exercise for EN/FR/DE.
    """
    lang = _validate_language(language)
    lv = _validate_level(level)
    topic_clean = (topic or 'daily conversation').strip() or 'daily conversation'

    vocabulary = _default_vocabulary(lang, topic_clean)
    exercise = _default_exercise(lang, topic_clean)

    return {
        'language': lang,
        'language_name': _SUPPORTED_LANGUAGES[lang],
        'level': lv,
        'topic': topic_clean,
        'objective': f'Practice {topic_clean} in {_SUPPORTED_LANGUAGES[lang]} ({lv}).',
        'vocabulary': vocabulary,
        'exercise': exercise,
        'feedback_rules': [
            'Correct grammar mistakes briefly.',
            'Suggest a more natural sentence.',
            'Ask one follow-up question in target language.',
        ],
    }


def build_classroom_system_prompt(language: str, level: str = 'beginner') -> str:
    """
    System prompt used by classroom websocket tutor.
    """
    lang = _validate_language(language)
    lv = _validate_level(level)
    language_name = _SUPPORTED_LANGUAGES[lang]

    return (
        f"You are a strict but friendly {language_name} tutor. "
        f"Student level is {lv}. Keep replies concise and pedagogical. "
        "Always include: 1) correction, 2) improved sentence, 3) one question to continue. "
        "Do not output ACTION lines or tool JSON. "
        "If student writes in Portuguese, translate and guide them into the target language."
    )


def _default_vocabulary(language: str, topic: str) -> List[Dict[str, str]]:
    topic_low = topic.lower()

    if 'restaurant' in topic_low or 'food' in topic_low:
        if language == 'fr':
            return [
                {'word': 'bonjour', 'meaning': 'hello'},
                {'word': 'je voudrais', 'meaning': 'I would like'},
                {'word': 'l’addition', 'meaning': 'the bill'},
            ]
        if language == 'de':
            return [
                {'word': 'Guten Tag', 'meaning': 'hello'},
                {'word': 'ich möchte', 'meaning': 'I would like'},
                {'word': 'die Rechnung', 'meaning': 'the bill'},
            ]
        return [
            {'word': 'hello', 'meaning': 'olá'},
            {'word': 'I would like', 'meaning': 'eu gostaria'},
            {'word': 'the bill', 'meaning': 'a conta'},
        ]

    if language == 'fr':
        return [
            {'word': 'bonjour', 'meaning': 'hello'},
            {'word': 'comment ça va', 'meaning': 'how are you'},
            {'word': 'au revoir', 'meaning': 'goodbye'},
        ]
    if language == 'de':
        return [
            {'word': 'Hallo', 'meaning': 'hello'},
            {'word': 'wie geht es dir', 'meaning': 'how are you'},
            {'word': 'tschüss', 'meaning': 'goodbye'},
        ]
    return [
        {'word': 'hello', 'meaning': 'olá'},
        {'word': 'how are you', 'meaning': 'como estás'},
        {'word': 'goodbye', 'meaning': 'adeus'},
    ]


def _default_exercise(language: str, topic: str) -> Dict[str, str]:
    if language == 'fr':
        return {
            'instruction': f"Écris 3 phrases sur le thème: {topic}.",
            'example': 'Bonjour, je voudrais un café, s’il vous plaît.',
        }
    if language == 'de':
        return {
            'instruction': f"Schreibe 3 Sätze zum Thema: {topic}.",
            'example': 'Guten Tag, ich möchte einen Kaffee, bitte.',
        }
    return {
        'instruction': f"Write 3 sentences about: {topic}.",
        'example': 'Hello, I would like a coffee, please.',
    }
