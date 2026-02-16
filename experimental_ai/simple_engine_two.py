#!/usr/bin/env python

import sys
import time
from queue import Empty, Queue
from threading import Event, Thread
import experimental_ai.utils.eval_glue as eval_glue

from pyrimaa.board import (
    BASIC_SETUP,
    BLANK_BOARD,
    Color,
    IllegalMove,
    Position,
    parse_short_pos,
)

from experimental_ai.utils.time_keeper import TimeKeeper


class _ComThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop = Event()
        self.messages = Queue()
        self.daemon = True

    def send(self, msg):
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()

    def run(self):
        while not self.stop.is_set():
            try:
                msg = sys.stdin.readline()
            except AttributeError:
                # during shutdown sys will change to None
                return
            self.messages.put(msg.strip())


class AEIException(Exception):
    pass


class AEIEngine:
    def __init__(self, controller):
        self.strict_checks = True
        self.move_delay = None
        self.total_move_time = 0.0
        self.controller = controller

        self.timekeeper = TimeKeeper(safety_margin_s=0.03)

        self.tc_move_s: float | None = None
        self.tc_turntime_s: float | None = None
        self.reserve_s = {Color.GOLD: 0.0, Color.SILVER: 0.0}

        try:
            header = controller.messages.get(30)
        except Empty:
            raise AEIException("Timed out waiting for aei header") from None
        if header != "aei":
            raise AEIException(f"Did not receive aei header, instead ({header})")
        controller.send("protocol-version 1")
        controller.send("id name Sample Engine")
        controller.send("id author Janzert")
        controller.send("aeiok")
        self.newgame()

    def newgame(self):
        self.position = Position(Color.GOLD, 4, BLANK_BOARD)
        self.insetup = True

        # IMPORTANT:
        # Do NOT reset tc_* here. The controller sets options (tcmove, tcturntime, etc.)
        # and then sends "newgame". If we reset them here, we ignore time controls and
        # will never use the available think time.
        #
        # Reserve values *can* be reset; the controller will keep updating greserve/sreserve.
        self.reserve_s = {Color.GOLD: 0.0, Color.SILVER: 0.0}

    def setposition(self, side_str, pos_str):
        side = "gswb".find(side_str) % 2
        self.position = parse_short_pos(side, 4, pos_str)
        self.insetup = False

    def setoption(self, name, value):
        std_opts = {
            "tcmove",
            "tcreserve",
            "tcpercent",
            "tcmax",
            "tctotal",
            "tcturns",
            "tcturntime",
            "greserve",
            "sreserve",
            "gused",
            "sused",
            "lastmoveused",
            "moveused",
            "opponent",
            "opponent_rating",
        }
        if name == "checkmoves":
            self.strict_checks = value.lower().strip() not in ["false", "no", "0"]
        elif name == "delaymove":
            self.move_delay = float(value)
        elif name == "tcmove" and value is not None:
            self.tc_move_s = float(value)
        elif name == "tcturntime" and value is not None:
            tt = float(value)
            # Convention: 0 means "no per-turn cap" in this controller codepath.
            self.tc_turntime_s = None if tt <= 0.0 else tt
        elif name == "greserve" and value is not None:
            self.reserve_s[Color.GOLD] = float(value)
        elif name == "sreserve" and value is not None:
            self.reserve_s[Color.SILVER] = float(value)
        elif name not in std_opts:
            self.log(f"Warning: Received unrecognized option, {name}")

    def _compute_budget_s(self, side: int) -> float | None:
        if self.tc_move_s is None:
            return None
        inc = float(self.tc_move_s)
        r = float(self.reserve_s.get(side, 0.0))

        reserve_fraction = 0.10
        reserve_cap = 0.50

        extra = min(r * reserve_fraction, reserve_cap)
        if r < 0.15:
            extra = min(extra, 0.05)

        budget = inc + extra

        # Only apply a cap if it is a positive number.
        if self.tc_turntime_s is not None and self.tc_turntime_s > 0.0:
            budget = min(budget, float(self.tc_turntime_s))

        return budget

    def makemove(self, move_str):
        try:
            self.position = self.position.do_move_str(move_str, self.strict_checks)
        except IllegalMove:
            self.log(f"Error: received illegal move {move_str}")
            return False
        if self.insetup and self.position.color == Color.GOLD:
            self.insetup = False
        return True

    def go(self):
        pos = self.position
        start_time = time.time()
        if self.insetup:
            setup = Position(Color.GOLD, 4, BASIC_SETUP)
            setup_moves = setup.to_placing_move()
            move_str = setup_moves[pos.color][2:]
        else:
            budget_s = self._compute_budget_s(pos.color)
            self.timekeeper.start_move(budget_s)

            steps, result = eval_glue.get_eval_step_move(pos, deadline=self.timekeeper.deadline)
            if steps is None:
                move_str = ""
                self.log("Warning: move requested when immobilized.")
            else:
                move_str = pos.steps_to_str(steps)

        if self.move_delay:
            time.sleep(self.move_delay)
        move_time = time.time() - start_time
        self.total_move_time += move_time
        self.info(f"time {round(move_time):.0f}")
        self.bestmove(move_str)

    def info(self, msg):
        self.controller.send("info " + msg)

    def log(self, msg):
        self.controller.send("log " + msg)

    def bestmove(self, move_str):
        self.controller.send("bestmove " + move_str)

    def main(self):
        ctl = self.controller
        while not ctl.stop.is_set():
            msg = ctl.messages.get()
            if msg == "isready":
                ctl.send("readyok")
            elif msg == "newgame":
                self.newgame()
            elif msg.startswith("setposition"):
                side, pos_str = msg.split(None, 2)[1:]
                self.setposition(side, pos_str)
            elif msg.startswith("setoption"):
                words = msg.split()
                name = words[2]
                v_ix = msg.find(name) + len(name)
                v_ix = msg.find("value", v_ix)
                if v_ix != -1:
                    value = msg[v_ix + 5 :]
                else:
                    value = None
                self.setoption(name, value)
            elif msg.startswith("makemove"):
                move_str = msg.split(None, 1)[1]
                if not self.makemove(move_str):
                    return
            elif msg.startswith("go"):
                if len(msg.split()) == 1:
                    self.go()
            elif msg == "stop":
                pass
            elif msg == "quit":
                self.log("Debug: Exiting after receiving quit message.")
                if self.total_move_time > 0:
                    self.info(f"move gen time {self.total_move_time}")
                return


def main():
    ctl = _ComThread()
    ctl.start()
    try:
        eng = AEIEngine(ctl)
        eng.main()
    finally:
        ctl.stop.set()


if __name__ == "__main__":
    main()