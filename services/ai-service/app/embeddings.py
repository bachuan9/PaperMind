import hashlib
import math
import re
from collections import Counter


VECTOR_DIMENSION = 256
TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def embed_text(text: str, dimension: int = VECTOR_DIMENSION) -> list[float]:
    """Build a stable, dependency-free text vector for local retrieval."""
    values = [0.0] * dimension
    features = Counter(feature for feature in feature_tokens(text))

    for feature, count in features.items():
        digest = hashlib.blake2b(
            feature.encode("utf-8"),
            digest_size=8,
        ).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] & 1 else -1.0
        values[bucket] += sign * math.log1p(count)

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [round(value / norm, 8) for value in values]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0

    dot_product = sum(left[index] * right[index] for index in range(len(left)))
    return dot_product / (left_norm * right_norm)


def feature_tokens(text: str) -> list[str]:
    features: list[str] = []
    for token in TOKEN_RE.findall(text.lower()):
        features.append(token)
        if contains_cjk(token):
            features.extend(
                f"cjk:{token[index:index + 2]}"
                for index in range(len(token) - 1)
            )
        elif len(token) > 3:
            features.extend(
                f"ngram:{token[index:index + 3]}"
                for index in range(len(token) - 2)
            )
    return features


def contains_cjk(token: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in token)
