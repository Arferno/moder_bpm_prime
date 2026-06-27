import pytest
from bot.utils.text import normalize_for_blacklist, check_blacklist_match, normalize_word_for_storage
from bot.database.models import BlacklistWord, BlacklistAction


class TestNormalizeForBlacklist:
    """Tests for text normalization."""

    def test_simple_lowercase(self):
        assert normalize_for_blacklist("привет") == "привет"

    def test_uppercase(self):
        assert normalize_for_blacklist("ПРИВЕТ") == "привет"

    def test_mixed_case(self):
        assert normalize_for_blacklist("ПрИвЕт") == "привет"

    def test_with_spaces(self):
        assert normalize_for_blacklist("п р и в е т") == "привет"

    def test_with_dots(self):
        assert normalize_for_blacklist("п.р.и.в.е.т") == "привет"

    def test_with_dashes(self):
        assert normalize_for_blacklist("п-р-и-в-е-т") == "привет"

    def test_with_underscores(self):
        assert normalize_for_blacklist("п_р_и_в_е_т") == "привет"

    def test_with_mixed_separators(self):
        assert normalize_for_blacklist("п.р-и_в е т") == "привет"

    def test_latin_letters(self):
        assert normalize_for_blacklist("HeLLo") == "hello"

    def test_latin_with_spaces(self):
        assert normalize_for_blacklist("h e l l o") == "hello"

    def test_mixed_cyrillic_latin(self):
        assert normalize_for_blacklist("пrиvеt") == "привет"

    def test_numbers_preserved(self):
        assert normalize_for_blacklist("привет123") == "привет123"

    def test_special_chars_removed(self):
        assert normalize_for_blacklist("п@р#и$в%е^т") == "привет"

    def test_empty_string(self):
        assert normalize_for_blacklist("") == ""

    def test_only_separators(self):
        assert normalize_for_blacklist(" . - _ ") == ""


class TestNormalizeWordForStorage:
    """Tests for word storage normalization."""

    def test_simple(self):
        assert normalize_word_for_storage("Мат") == "мат"

    def test_with_spaces(self):
        assert normalize_word_for_storage("п р и в е т") == "привет"


class TestCheckBlacklistMatch:
    """Tests for blacklist matching."""

    @pytest.fixture
    def blacklist_words(self):
        return [
            BlacklistWord(id=1, word="мат", normalized_word="мат", action=BlacklistAction.WARN),
            BlacklistWord(id=2, word="реклама", normalized_word="реклама", action=BlacklistAction.MUTE),
            BlacklistWord(id=3, word="спам", normalized_word="спам", action=BlacklistAction.DELETE),
        ]

    def test_exact_match(self, blacklist_words):
        matched, word = check_blacklist_match("Это мат", blacklist_words)
        assert matched is True
        assert word.word == "мат"

    def test_match_with_spaces(self, blacklist_words):
        matched, word = check_blacklist_match("м а т", blacklist_words)
        assert matched is True
        assert word.word == "мат"

    def test_match_with_dots(self, blacklist_words):
        matched, word = check_blacklist_match("м.а.т", blacklist_words)
        assert matched is True

    def test_match_uppercase(self, blacklist_words):
        matched, word = check_blacklist_match("МАТ", blacklist_words)
        assert matched is True

    def test_match_mixed_case(self, blacklist_words):
        matched, word = check_blacklist_match("МаТ", blacklist_words)
        assert matched is True

    def test_no_match(self, blacklist_words):
        matched, word = check_blacklist_match("привет мир", blacklist_words)
        assert matched is False
        assert word is None

    def test_partial_word_no_match(self, blacklist_words):
        # "математика" should not match "мат"
        matched, word = check_blacklist_match("математика", blacklist_words)
        assert matched is False

    def test_multiple_words_first_matches(self, blacklist_words):
        matched, word = check_blacklist_match("реклама и спам", blacklist_words)
        assert matched is True
        assert word.word == "реклама"  # First in list

    def test_empty_text(self, blacklist_words):
        matched, word = check_blacklist_match("", blacklist_words)
        assert matched is False

    def test_empty_blacklist(self):
        matched, word = check_blacklist_match("мат", [])
        assert matched is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])