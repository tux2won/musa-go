from src.retrieval import HybridRetriever


def test_disease_prevention_retrieval():
    retriever = HybridRetriever.load()
    hits = retriever.search("쯔쯔가무시증 야외활동 예방수칙", top_k=5)
    assert any("쯔쯔가무시증" in hit.chunk["disease_tags"] for hit in hits)
    assert any("prevention" in hit.chunk["intent_tags"] for hit in hits)


def test_military_care_retrieval():
    retriever = HybridRetriever.load()
    hits = retriever.search("장병이 아프면 군병원과 민간병원 중 어디에서 진료받나요?", top_k=5)
    assert any("military_care" in hit.chunk["intent_tags"] for hit in hits)
    assert any(hit.chunk["authority_level"] == "A" for hit in hits)


def test_unverified_card_terms_are_not_returned_by_default():
    retriever = HybridRetriever.load()
    hits = retriever.search("나라사랑카드 보험이 말라리아 진료비를 보장하나요?", top_k=5)
    assert hits == []
    historical = retriever.search(
        "나라사랑카드 과거 약관 원문 근거를 보여줘",
        top_k=5,
        include_historical=True,
    )
    assert any(hit.chunk["effective_status"] == "historical_unverified" for hit in historical)
