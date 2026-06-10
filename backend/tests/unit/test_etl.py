"""Unit tests for the ETL pipeline's pure functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.etl.build_lexicon import extract_wikt_entry, gender_to_article, merge_entry
from scripts.etl.build_sentences import grade_sentence, make_cloze
from scripts.etl.common import content_tokens, tokenize_nl
from scripts.etl.validate import check_article_plural, check_story_coverage

from app.services.content_generator import story_coverage


class TestTokenizer:
    def test_tokenize_lowercases_and_splits(self):
        assert tokenize_nl("De hond loopt!") == ["de", "hond", "loopt"]

    def test_content_tokens_drops_stopwords(self):
        assert content_tokens("De hond loopt in het park") == ["hond", "loopt", "park"]


class TestGenderToArticle:
    def test_neuter_category_maps_to_het(self):
        entry = {"categories": [{"name": "Dutch neuter nouns"}]}
        assert gender_to_article(entry) == "het"

    def test_masculine_category_maps_to_de(self):
        entry = {"categories": [{"name": "Dutch masculine nouns"}]}
        assert gender_to_article(entry) == "de"

    def test_head_template_fallback(self):
        entry = {"categories": [], "head_templates": [{"args": {"g": "n"}}]}
        assert gender_to_article(entry) == "het"

    def test_unknown_gender_returns_none(self):
        assert gender_to_article({"categories": []}) is None


class TestExtractWiktEntry:
    def test_extracts_noun_fields(self):
        entry = {
            "word": "Huis",
            "pos": "noun",
            "lang_code": "nl",
            "categories": [{"name": "Dutch neuter nouns"}],
            "forms": [{"form": "huizen", "tags": ["plural"]}],
            "sounds": [{"ipa": "/ɦœys/"}],
            "senses": [{"translations": [{"lang_code": "es", "word": "casa"}]}],
        }
        result = extract_wikt_entry(entry)
        assert result == {
            "lemma": "huis",
            "pos": "noun",
            "article": "het",
            "plural": "huizen",
            "ipa": "/ɦœys/",
            "es_candidates": ["casa"],
            "separable": False,
        }

    def test_skips_non_dutch(self):
        assert extract_wikt_entry({"word": "house", "pos": "noun", "lang_code": "en"}) is None


class TestMergeEntry:
    def test_nt2lex_level_attached(self):
        wikt = {"lemma": "huis", "pos": "noun", "article": "het", "plural": "huizen",
                "ipa": None, "es_candidates": [], "separable": False}
        row, conflict = merge_entry(wikt, {("huis", "noun"): "a1"})
        assert row["cefr_level"] == "a1"

    def test_level_falls_back_to_any_pos(self):
        wikt = {"lemma": "lopen", "pos": "verb", "article": None, "plural": None,
                "ipa": None, "es_candidates": [], "separable": False}
        row, _ = merge_entry(wikt, {("lopen", "ww"): "a1"})
        assert row["cefr_level"] == "a1"


class TestGradeSentence:
    LEXICON = {
        "hond": {"cefr_level": "a1"},
        "loopt": {"cefr_level": "a1"},
        "park": {"cefr_level": "a2"},
    }

    def test_level_is_max_of_content_lemmas(self):
        level, coverage = grade_sentence("De hond loopt in het park", self.LEXICON)
        assert level == "a2"
        assert coverage == 1.0

    def test_unknown_token_grades_unk(self):
        level, coverage = grade_sentence("De fluxcapaciteit loopt", self.LEXICON)
        assert level == "unk"
        assert coverage < 1.0


class TestMakeCloze:
    def test_blanks_target_lemma(self):
        assert make_cloze("De hond loopt.", "hond") == "De ___ loopt."

    def test_returns_none_when_absent(self):
        assert make_cloze("De kat slaapt.", "hond") is None


class TestArticlePluralGate:
    LEXICON = {"huis": {"pos": "noun", "article": "het", "plural": "huizen"}}

    def test_wrong_article_is_hard_fail(self):
        item = {"dutch_word": "huis", "article": "de"}
        errors = check_article_plural(item, self.LEXICON)
        assert len(errors) == 1
        assert "article mismatch" in errors[0]

    def test_correct_article_passes(self):
        item = {"dutch_word": "huis", "article": "het", "plural": "huizen"}
        assert check_article_plural(item, self.LEXICON) == []

    def test_word_not_in_lexicon_passes(self):
        assert check_article_plural({"dutch_word": "xyz", "article": "de"}, self.LEXICON) == []


class TestStoryCoverageGate:
    def test_full_coverage_passes(self):
        known = {"hond", "loopt", "park", "kat", "slaapt"}
        assert check_story_coverage("De hond loopt. De kat slaapt.", known) == []

    def test_low_coverage_fails(self):
        errors = check_story_coverage("De fluxcapaciteit resoneert enorm vandaag", {"hond"})
        assert any("coverage" in e for e in errors)

    def test_undeclared_new_words_flagged(self):
        known = {"hond", "loopt", "kat", "slaapt", "eet", "drinkt", "speelt", "ziet",
                 "huis", "boom", "water", "brood", "melk", "vis", "vogel", "tuin",
                 "straat", "auto", "fiets", "winkel"}
        errors = check_story_coverage(
            "De hond loopt. De kat slaapt. De vogel zingt.", known, declared_new=[]
        )
        assert any("undeclared" in e for e in errors)


class TestServiceStoryCoverage:
    def test_known_story_has_full_coverage(self):
        coverage, unknown = story_coverage("De hond loopt.", {"hond", "loopt"})
        assert coverage == 1.0
        assert unknown == []

    def test_unknown_words_reported(self):
        coverage, unknown = story_coverage("De hond zwemt.", {"hond"})
        assert coverage == 0.5
        assert unknown == ["zwemt"]
