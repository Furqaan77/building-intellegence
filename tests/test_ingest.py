from building_with_rag.ingest import ACTS, Line, parse_ipc, to_record


def test_ipc_section_record_format():
    lines = [
        Line(1, "CHAPTER XVI"),
        Line(1, "OF OFFENCES AFFECTING THE HUMAN BODY"),
        Line(1, "302."),
        Line(1, "Punishment for murder."),
        Line(1, "302. Punishment for murder.--Whoever commits murder shall be punished"),
        Line(2, "with death."),
    ]
    sections = parse_ipc(lines)
    record = to_record(sections[0], ACTS["ipc"], "ipc", "0" * 64, "x")

    assert record["section_id"] == "ipc:302"
    assert record["act"] == "IPC_1860"
    assert record["status"] == "repealed"
    assert record["chapter"] == "XVI"
    assert record["section_number"] == 302
    assert record["heading"] == "Punishment for murder."
    assert record["text"] == "Whoever commits murder shall be punished with death."
    assert (record["page_start"], record["page_end"]) == (1, 2)
    assert record["needs_review"] is False


def test_lettered_section_is_kept_and_flagged():
    lines = [
        Line(1, "CHAPTER XVI"),
        Line(1, "OF OFFENCES"),
        Line(1, "376A."),
        Line(1, "Heading."),
        Line(1, "376A. Heading.--Text."),
    ]
    record = to_record(parse_ipc(lines)[0], ACTS["ipc"], "ipc", "0" * 64, "x")
    assert record["section_id"] == "ipc:376A"
    assert record["section_number"] == 376
    assert record["needs_review"] is True
