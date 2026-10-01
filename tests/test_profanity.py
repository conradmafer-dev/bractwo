"""Representative public-comment profanity and false-positive regressions."""
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.profanity import contains_profanity


class ProfanityTests(unittest.TestCase):
    def assert_detected(self, examples):
        for text in examples:
            with self.subTest(text=text):
                self.assertTrue(contains_profanity(text))

    def test_polish_inflections_and_sentence_punctuation(self):
        self.assert_detected([
            "Ale kurwa!", "(kurwy)", "kurwie", "skurwysynem", "chuj",
            "chujowy komentarz", "huj", "jebany", "zajebiste", "zajebiście",
            "jebali", "wyjebany", "Nie pierdol.", "pierdolić", "pierdolona",
            "spierdalaj", "wypierdalajcie", "gówno", "gówniany", "dupie",
            "dupek", "cipka", "pizda", "dziwka", "wkurwiony", "zjeb",
            "skurwiel", "japierdole", "kurwiarz", "pierdolnij", "pierdolcie",
            "jebnięty", "zajebisty",
        ])

    def test_unicode_case_and_invisible_characters(self):
        self.assert_detected([
            "KURWA", "ＫＵＲＷＡ", "𝕜𝕦𝕣𝕨𝕒", "kúrwá", "GÓWNO",
            "ku\u200brwa", "ku\u200drwa", "kur\u2060wa", "ku\ufeffrwa",
            "go\u0301wno", "PIERDOLIĆ",
        ])

    def test_common_separator_repeat_leet_and_mask_evasions(self):
        self.assert_detected([
            "k.u.r.w.a", "k u r w a", "k_u_r_w_a", "ku-rwa", "ch uj",
            "KUUUURRRWWWAAAA!!!", "pierdolllic", "shiiit", "assss",
            "p13rd0l", "g0wn0", "kurw4", "b1tch", "sh!t", "$hit",
            "k**wa", "ku*wa", "kur*a", "ch*j", "f**k", "s**t", "j***ć",
            "*kurwa*", "c*h*u*j", "f u c k", "a.s.s.h.o.l.e",
        ])

    def test_common_english_words_and_inflections(self):
        self.assert_detected([
            "fuck", "fucking", "fucker", "motherfucker", "shit", "shitty",
            "bullshit", "bitch", "bitches", "cunt", "dickhead", "asshole",
            "ass", "piss", "pissed", "bastards", "whore", "sluts",
        ])

    def test_neutral_polish_and_english_are_not_substring_matches(self):
        for text in [
            "", "Dziękuję za grę! Świetny polski MMORPG.",
            "Słuchaj, kucharz może podupadać na zdrowiu.",
            "SŁUCHAJ! Kucharz. Podupadać.",
            "Scunthorpe, Dickinson, Pissarro i klasyczna muzyka.",
            "class assignment, passage, assistance, butterfly, shitake, shiitake",
            "PiS", "pis", "as", "las", "pas", "kultura", "kurtyna",
            "Kurka, cukier i pieprz są w kuchni.",
            "Czary I–IX kręgu, 4 klasy i drużyny do 4 osób.",
            "Ku chwale bractwa! Urwał się pasek, a gra nadal działa.",
            "Bardzo fajna gra. Polecam!", "Łucznik jest suuuper!",
            "**Dobra gra** i *świetna muzyka*.",
            "https://example.org/scunthorpe oraz gracz@example.org",
            "Przygotuj tarczę. Chodź na wyprawę, Ula.",
        ]:
            with self.subTest(text=text):
                self.assertFalse(contains_profanity(text))

    def test_long_input_and_repeated_letters_remain_bounded(self):
        self.assertFalse(contains_profanity("dobra " * 1000))
        self.assertFalse(contains_profanity("a" * 5000))
        self.assertTrue(contains_profanity("k" + "u" * 5000 + "rwa"))

    def test_many_distinct_censored_tokens_and_final_profanity(self):
        rng = random.Random(42)
        neutral = " ".join(rng.choice("xzqv") + "*" + rng.choice("xzqv")
                           for _ in range(250))
        self.assertFalse(contains_profanity(neutral))
        self.assertTrue(contains_profanity(neutral[:991] + " kurwa"))
        self.assertFalse(contains_profanity("\ufdfa" * 1000))
        expanded = "".join("\ufdfa" + chr(0x4e00 + index) for index in range(500))
        self.assertFalse(contains_profanity(expanded))
        self.assertTrue(contains_profanity(expanded[:990] + " kurwa"))


if __name__ == "__main__":
    unittest.main()
