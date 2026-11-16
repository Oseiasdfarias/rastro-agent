from rootcause.adapters.manuals.ingest import chunk_pages


def test_chunk_overlap():
    text = "".join(chr(65 + i % 26) for i in range(2000))
    chunks = chunk_pages([text], size=800, overlap=150, first_page=1)
    assert len(chunks) == 3
    assert chunks[0][1][-150:] == chunks[1][1][:150]


def test_chunk_keeps_page_number():
    chunks = chunk_pages(["a" * 100, "", "b" * 900], size=800, overlap=150, first_page=157)
    assert [p for p, _ in chunks] == [157, 159, 159]
