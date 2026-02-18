import unittest

from pyrimaa.notation_translator import (
    NotationTranslationError,
    internal_side_to_db_side,
    translate_game_lines_internal_to_db,
    translate_game_string_internal_to_db,
    translate_move_line_internal_to_db,
)


class TestNotationTranslator(unittest.TestCase):
    def test_internal_side_to_db_side(self):
        self.assertEqual(internal_side_to_db_side("g"), "w")
        self.assertEqual(internal_side_to_db_side("G"), "w")
        self.assertEqual(internal_side_to_db_side("s"), "b")
        self.assertEqual(internal_side_to_db_side("S"), "b")
        with self.assertRaises(NotationTranslationError):
            internal_side_to_db_side("w")
        with self.assertRaises(NotationTranslationError):
            internal_side_to_db_side("")
        with self.assertRaises(NotationTranslationError):
            internal_side_to_db_side("gs")

    def test_translate_move_line_steps(self):
        internal = "9s de6w Re5n Re6e Rf6x de7s"
        expected = "9b de6w Re5n Re6e Rf6x de7s"
        self.assertEqual(translate_move_line_internal_to_db(internal), expected)

    def test_translate_move_line_setup(self):
        internal = "1g Ra1 Rb1 Rc1 Rd1 Re1 Rf1 Rg1 Ch1 Ha2 Mb2 Dc2 Dd2 Ee2 Cf2 Hg2 Rh2"
        expected = "1w Ra1 Rb1 Rc1 Rd1 Re1 Rf1 Rg1 Ch1 Ha2 Mb2 Dc2 Dd2 Ee2 Cf2 Hg2 Rh2"
        self.assertEqual(translate_move_line_internal_to_db(internal), expected)

        internal2 = "1s ra8 rb8 rc8 dd8 de8 rf8 rg8 rh8 hb7 ra7 cc7 ed7 me7 cf7 rh7 hg7"
        expected2 = "1b ra8 rb8 rc8 dd8 de8 rf8 rg8 rh8 hb7 ra7 cc7 ed7 me7 cf7 rh7 hg7"
        self.assertEqual(translate_move_line_internal_to_db(internal2), expected2)

    def test_translate_move_line_strips_and_normalizes_whitespace(self):
        internal = "  10g   md3w mc3x   Ed4s   Ha2e Hb2n   "
        expected = "10w md3w mc3x Ed4s Ha2e Hb2n"
        self.assertEqual(translate_move_line_internal_to_db(internal), expected)

    def test_translate_move_line_allows_no_rest(self):
        self.assertEqual(translate_move_line_internal_to_db("11g"), "11w")
        self.assertEqual(translate_move_line_internal_to_db("11s   "), "11b")

    def test_translate_move_line_rejects_bad_headers(self):
        bad = [
            "",
            "   ",
            "g1 Ra1",  # side before number
            "1w Ra1",  # already db side, not internal
            "1b ra8",  # already db side, not internal
            "1x Ee2n",  # unsupported side
            "move 1g Ee2n",
        ]
        for line in bad:
            with self.subTest(line=line):
                with self.assertRaises(NotationTranslationError):
                    translate_move_line_internal_to_db(line)

    def test_translate_game_lines(self):
        internal_lines = [
            "1g Ra1 Rb1",
            "1s ra8 rb8",
            "2g Ee2n Ee3n",
            "2s ed7s me7w",
        ]
        expected = [
            "1w Ra1 Rb1",
            "1b ra8 rb8",
            "2w Ee2n Ee3n",
            "2b ed7s me7w",
        ]
        self.assertEqual(translate_game_lines_internal_to_db(internal_lines), expected)

    def test_translate_game_string(self):
        internal = "\n".join(
            [
                "1g Ra1 Rb1",
                "1s ra8 rb8",
                "",
                "  2g Ee2n Ee3n  ",
                "2s ed7s me7w",
            ]
        )
        expected = "\n".join(
            [
                "1w Ra1 Rb1",
                "1b ra8 rb8",
                "2w Ee2n Ee3n",
                "2b ed7s me7w",
            ]
        )
        self.assertEqual(translate_game_string_internal_to_db(internal), expected)

    def test_translate_game_string_rejects_none(self):
        with self.assertRaises(NotationTranslationError):
            translate_game_string_internal_to_db(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()