import os
import re

# Upstream uses llama_index (VectorStoreIndex over data/*.md). To keep this
# starter dependency-light we ship the same data files and answer with a
# simple keyword-overlap retrieval instead — swap in your favourite RAG stack
# here if you want real semantic search.

data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

_STOPWORDS = {
    "a", "an", "and", "the", "of", "in", "on", "for", "with", "to", "is",
    "who", "that", "about", "me", "my", "some", "give", "i", "want", "like",
}


def _tokens(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOPWORDS}


def _paragraphs():
    for root, _dirs, files in os.walk(data_path):
        for filename in files:
            if not filename.endswith(".md"):
                continue
            with open(os.path.join(root, filename), encoding="utf-8") as f:
                for para in f.read().split("\n\n"):
                    para = para.strip()
                    if para:
                        yield para


def get_character_inspiration(inspiration):
    fallbackResponse = {
        "result": "Sorry, I am dealing with a technical issue at the moment, perhaps because of heightened user traffic. Come back later and we can try this again. Apologies for that."
    }
    if inspiration:
        try:
            if os.path.exists(data_path):
                query = _tokens(inspiration)
                best, best_score = None, 0.0
                for para in _paragraphs():
                    overlap = query & _tokens(para)
                    score = len(overlap) / max(len(query), 1)
                    if score > best_score:
                        best, best_score = para, score

                if best is None:
                    return fallbackResponse

                return {
                    "result": best,
                    "score": round(best_score, 3),
                }
            else:
                return fallbackResponse
        except Exception:
            return fallbackResponse
    else:
        return fallbackResponse
