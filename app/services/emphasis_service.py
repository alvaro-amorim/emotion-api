from app.api.schemas import EmphasisWord


def select_emphasis_words(words: list[EmphasisWord]) -> list[EmphasisWord]:
    return sorted(words, key=lambda item: item.emphasis_score, reverse=True)

