from backend.processing import chunk_text, clean_text


def test_short_text_single_chunk():
    assert chunk_text("Attendance must be 75%.") == ["Attendance must be 75%."]


def test_long_text_is_split_with_size_limit():
    text = " ".join(f"Sentence number {i} about policy." for i in range(200))
    chunks = chunk_text(text, size=400, overlap=60)
    assert len(chunks) > 3
    assert all(len(c) <= 400 + 60 for c in chunks)


def test_empty_text():
    assert chunk_text("   ") == []


def test_clean_text_joins_hyphenation():
    assert clean_text("exami-\nnation  rules") == "examination rules"
