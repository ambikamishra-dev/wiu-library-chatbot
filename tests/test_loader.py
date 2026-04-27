import pytest
from pathlib import Path
from app.core.loader import load_faq, get_quick_buttons, FAQEntry


@pytest.fixture(scope="session")
def faq_entries():

    return load_faq(force_reload=True)


@pytest.fixture(scope="session")
def faq_by_id(faq_entries):

    return {e.faq_id: e for e in faq_entries}


def test_load_faq_returns_correct_count(faq_entries):

    assert len(faq_entries) == 11, (
        f"Expected 11 FAQ entries, got {len(faq_entries)}. "
        "Check if an entry was accidentally deactivated in the Excel file."
    )


def test_all_entries_are_faqentry_instances(faq_entries):

    for entry in faq_entries:
        assert isinstance(entry, FAQEntry), (
            f"Entry {entry} is not a FAQEntry instance"
        )


def test_all_required_fields_present(faq_entries):

    for entry in faq_entries:
        assert entry.faq_id, f"Empty faq_id found"
        assert entry.question, f"Empty question in FAQ {entry.faq_id}"
        assert entry.answer, f"Empty answer in FAQ {entry.faq_id}"


def test_no_duplicate_faq_ids(faq_entries):

    ids = [e.faq_id for e in faq_entries]
    assert len(ids) == len(set(ids)), (
        f"Duplicate faq_ids found: {[i for i in ids if ids.count(i) > 1]}"
    )


def test_all_entries_are_active(faq_entries):

    for entry in faq_entries:
        assert entry.active is True, (
            f"Inactive entry {entry.faq_id} was returned by load_faq()"
        )


def test_cache_returns_same_object():

    first = load_faq()
    second = load_faq()
    assert first is second, "Cache broken — load_faq() is re-reading file on every call"


def test_force_reload_re_reads_file():

    first = load_faq()
    second = load_faq(force_reload=True)
    # Different object but same content
    assert first is not second
    assert len(first) == len(second)


def test_multi_url_faq_004(faq_by_id):

    entry = faq_by_id["004"]
    assert len(entry.urls) == 2, (
        f"FAQ 004 should have 2 URLs, got {len(entry.urls)}"
    )


def test_multi_url_faq_006(faq_by_id):
    """FAQ 006 has two URLs — I-Share and ILLiad."""
    entry = faq_by_id["006"]
    assert len(entry.urls) == 2


def test_multi_url_faq_010(faq_by_id):
    """FAQ 010 has two URLs — classroom calendar and request form."""
    entry = faq_by_id["010"]
    assert len(entry.urls) == 2


def test_single_url_entries_have_one_url(faq_by_id):

    for faq_id in ["001", "002", "003", "005", "007", "008", "011"]:
        entry = faq_by_id[faq_id]
        assert len(entry.urls) == 1, (
            f"FAQ {faq_id} should have 1 URL, got {len(entry.urls)}"
        )


def test_no_url_entry_has_empty_list(faq_by_id):

    entry = faq_by_id["009"]
    assert entry.urls == [], (
        "FAQ 009 should have empty urls list, got None or non-empty"
    )


def test_all_urls_have_https_scheme(faq_entries):

    for entry in faq_entries:
        for url_dict in entry.urls:
            assert url_dict["url"].startswith("https://"), (
                f"FAQ {entry.faq_id} has URL without https://: {url_dict['url']}"
            )


def test_all_url_dicts_have_required_keys(faq_entries):
    """Every URL dict must have both 'url' and 'label' keys."""
    for entry in faq_entries:
        for url_dict in entry.urls:
            assert "url" in url_dict, f"Missing 'url' key in FAQ {entry.faq_id}"
            assert "label" in url_dict, f"Missing 'label' key in FAQ {entry.faq_id}"


def test_keywords_are_lowercase(faq_entries):

    for entry in faq_entries:
        for kw in entry.keywords:
            assert kw == kw.lower(), (
                f"FAQ {entry.faq_id} has non-lowercase keyword: '{kw}'"
            )


def test_keywords_have_no_extra_whitespace(faq_entries):
    """Keywords must be stripped — trailing spaces break exact matching."""
    for entry in faq_entries:
        for kw in entry.keywords:
            assert kw == kw.strip(), (
                f"FAQ {entry.faq_id} has keyword with whitespace: '{kw}'"
            )


def test_all_entries_have_at_least_one_keyword(faq_entries):

    for entry in faq_entries:
        assert len(entry.keywords) > 0, (
            f"FAQ {entry.faq_id} has no keywords — will never match in Stage 1"
        )


def test_quick_buttons_count():

    buttons = get_quick_buttons()
    assert len(buttons) == 6, (
        f"Expected 6 quick buttons, got {len(buttons)}"
    )


def test_quick_buttons_are_subset_of_entries(faq_entries):

    all_ids = {e.faq_id for e in faq_entries}
    for btn in get_quick_buttons():
        assert btn.faq_id in all_ids, (
            f"Quick button {btn.faq_id} not found in main FAQ entries"
        )


def test_missing_file_raises_file_not_found(tmp_path, monkeypatch):

    monkeypatch.setattr("app.core.loader.settings.faq_file_path",
                        str(tmp_path / "missing.xlsx"))
    with pytest.raises(FileNotFoundError):
        load_faq(force_reload=True)


def test_wrong_extension_raises_value_error(tmp_path, monkeypatch):

    wrong_file = tmp_path / "faq.csv"
    wrong_file.write_text("some,csv,data")
    monkeypatch.setattr(
        "app.core.loader.settings.faq_file_path", str(wrong_file))
    with pytest.raises(ValueError, match="Expected .xlsx"):
        load_faq(force_reload=True)
