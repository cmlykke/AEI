import threading
import unittest
from queue import Queue

from pyrimaa.board import BASIC_SETUP, Color, IllegalMove, Position

from experimental_ai.engines.heuristic.simple_engine_two.engine import AEIEngine

class _FakeController:
    """
    Minimal in-process AEI controller stub.

    - `messages` is what the engine reads from (incoming controller->engine commands).
    - `send(...)` is what the engine writes to (engine->controller responses).
    """

    def __init__(self) -> None:
        self.messages: Queue[str] = Queue()
        self.stop = threading.Event()

        self.sent: list[str] = []
        self._sent_lock = threading.Lock()

        self.bestmove_event = threading.Event()
        self.bestmove_line: str | None = None

    def send(self, msg: str) -> None:
        with self._sent_lock:
            self.sent.append(msg)
            if msg.startswith("bestmove "):
                self.bestmove_line = msg
                self.bestmove_event.set()


class TestSimpleEngineTwoIntegration(unittest.TestCase):
    def test_engine_responds_with_legal_move(self) -> None:
        ctl = _FakeController()

        # Engine constructor blocks waiting for the AEI header.
        ctl.messages.put("aei")
        eng = AEIEngine(ctl)

        # Run the engine main loop in a background thread so we can "talk" to it.
        t = threading.Thread(target=eng.main, daemon=True)
        t.start()

        # Ensure handshake completed (constructor should have sent these).
        # (We avoid being overly strict about the exact id strings.)
        self.assertTrue(any(line == "aeiok" for line in ctl.sent), msg=f"sent={ctl.sent!r}")

        # Provide a normal midgame-ish position (basic setup, gold to move).
        pos = Position(Color.GOLD, 4, BASIC_SETUP)
        short = pos.board_to_str("short")
        ctl.messages.put("newgame")
        ctl.messages.put(f"setposition g {short}")

        # Give it a small (but non-zero) budget so we exercise the deadline-aware path.
        ctl.messages.put("setoption name tcmove value 0.15")
        ctl.messages.put("setoption name greserve value 0.0")
        ctl.messages.put("setoption name sreserve value 0.0")

        ctl.messages.put("go")

        # Wait for a bestmove response.
        got = ctl.bestmove_event.wait(timeout=5.0)
        try:
            self.assertTrue(got, msg=f"Timed out waiting for bestmove. sent={ctl.sent!r}")
            assert ctl.bestmove_line is not None  # for type checkers

            move_str = ctl.bestmove_line.removeprefix("bestmove ").strip()
            self.assertNotEqual(move_str, "", msg="Engine returned empty move unexpectedly.")

            # Validate: move parses and is legal from the position we provided.
            try:
                next_pos = pos.do_move_str(move_str, strict_checks=True)
            except IllegalMove as e:
                self.fail(f"Engine produced an illegal move: {move_str!r}. Error: {e}")

            # Sanity: the move should change the position and pass the turn.
            self.assertNotEqual(next_pos.bitBoards, pos.bitBoards)
            self.assertNotEqual(next_pos.color, pos.color)

        finally:
            # Clean shutdown
            ctl.messages.put("quit")
            ctl.stop.set()
            t.join(timeout=1.0)
            # If it didn't join, it's daemon=True so the test run won't hang.


if __name__ == "__main__":
    unittest.main()