from src.coverage_engine import CoverageEngine, ROUTE_ORDER, _portable_relative_path


def test_source_paths_are_portable_across_windows_and_linux():
    assert _portable_relative_path(r"0702\evidence.md").parts == ("0702", "evidence.md")
    assert _portable_relative_path("0702/evidence.md").parts == ("0702", "evidence.md")


def test_all_scenarios_have_four_ordered_routes_and_valid_sources():
    engine = CoverageEngine()
    assert set(engine.scenarios) == {
        "prepare",
        "symptoms",
        "military_care",
        "civilian_needed",
        "already_paid",
    }
    for scenario_id in engine.scenarios:
        scenario = engine.get(scenario_id)
        assert [route.route_type for route in scenario.routes] == ROUTE_ORDER
        for route in scenario.routes:
            if route.certainty_status == "evidence_gap":
                assert route.source_path is None
            else:
                assert route.source_path and route.source_path.exists()


def test_urgent_scenarios_prioritize_care():
    engine = CoverageEngine()
    assert engine.get("symptoms").urgent_first
    assert engine.get("civilian_needed").urgent_first
    assert "비용보다 진료가 먼저" in engine.get("symptoms").summary


def test_already_paid_scenario_preserves_key_documents():
    engine = CoverageEngine()
    scenario = engine.get("already_paid")
    all_text = " ".join(scenario.checklist) + " " + " ".join(
        document for route in scenario.routes for document in route.documents_to_check
    )
    assert "영수증" in all_text
    assert "세부산정내역서" in all_text
    assert "처방전" in all_text


def test_private_insurance_is_always_an_evidence_gap_not_a_product_recommendation():
    engine = CoverageEngine()
    for scenario_id in engine.scenarios:
        route = next(route for route in engine.get(scenario_id).routes if route.route_type == "private_insurance")
        assert route.certainty_status == "evidence_gap"
        assert "추천" in route.interpretation_warning or "판정" in route.cost_responsibility_status or "확인" in route.first_action
        assert not route.source_file


def test_no_sensitive_identity_fields_are_collected_by_rules():
    engine = CoverageEngine()
    forbidden = {"resident_number", "diagnosis", "policy_number", "name", "phone"}
    assert forbidden.isdisjoint(vars(engine.get("prepare")))
