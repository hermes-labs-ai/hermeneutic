from hermeneutic.hermes_agent_plugin import check_outgoing_claims, register


def test_clean_and_low_severity_responses_pass_through() -> None:
    assert check_outgoing_claims("The targeted test passed.") is None
    assert check_outgoing_claims("This is a robust starting point.") is None


def test_actionable_evidence_obligation_is_appended_before_delivery() -> None:
    response = "Done — shipped 14 files, all tests pass."

    transformed = check_outgoing_claims(response)

    assert transformed is not None
    assert transformed.startswith(response)
    assert "Hermeneutic evidence check: high" in transformed
    assert "completion_with_number" in transformed
    assert "completion_with_all_quantifier" in transformed


def test_register_uses_native_final_output_hook() -> None:
    class Context:
        def __init__(self) -> None:
            self.registrations: list[tuple[str, object]] = []

        def register_hook(self, name: str, callback: object) -> None:
            self.registrations.append((name, callback))

    ctx = Context()
    register(ctx)

    assert ctx.registrations == [("transform_llm_output", check_outgoing_claims)]
