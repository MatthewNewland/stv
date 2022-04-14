from __future__ import annotations
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Mapping, Optional
# import threading
# from time import sleep
import string

import typer


Candidate = str


@dataclass
class Ballot:
    ranking: list[Candidate]
    weight: int | float = 1

    @property
    def current_preference(self) -> Candidate:
        try:
            return self.ranking[0]
        except IndexError:
            return None

    def drop(self, candidate: Candidate):
        try:
            self.ranking.remove(candidate)
        except ValueError:
            pass


@dataclass
class Round:
    winners: Optional[list[Candidate]]
    loser: Optional[Candidate]
    scores: Mapping[Candidate, int | float]


class Election:
    hopefuls: list[Candidate]
    ballots: list[Ballot]
    seats: int
    winners: list[Candidate]
    losers: list[Candidate]
    rounds: list[Round]

    def __init__(self, candidates: list[Candidate], ballots: list[Ballot], seats: int = 1):
        self.hopefuls = candidates
        self.ballots = ballots
        self.seats = seats
        self.winners = []
        self.losers = []
        self.rounds = []

    @property
    def threshold(self) -> int | float:
        return len(self.ballots) / (self.seats + 1)

    def run_election(self):
        # threading.Timer(5.0, lambda: print(f"{self.winners=} {self.hopefuls=} {self.losers=}")).start()
        while len(self.winners) < self.seats:
            scores = {}
            for cand in self.hopefuls:
                scores[cand] = self.threshold if cand in self.winners else 0

            for ballot in self.ballots:
                if ballot.current_preference is None:
                    continue
                scores[ballot.current_preference] += ballot.weight

            round_winners = [cand for cand in self.hopefuls if scores[cand] > self.threshold]

            if len(round_winners) > 0:
                # Surplus transfer round
                self.winners.extend(round_winners)
                self.rounds.append(Round(winners=round_winners, loser=None, scores=scores))
                for winner in round_winners:
                    self.hopefuls.remove(winner)
                self.transfer_surplus(scores)
            else:
                self.eliminate_losers(scores)

            if len(self.winners) + len(self.hopefuls) < self.seats:
                while len(self.winners) < self.seats:
                    self.winners.append(self.losers.pop())

    def transfer_surplus(self, scores):
        for ballot in self.ballots:
            if ballot.current_preference in self.winners:
                surplus = (scores[ballot.current_preference] - self.threshold) / scores[ballot.current_preference]
                ballot.weight *= surplus
                ballot.drop(ballot.current_preference)

    def eliminate_losers(self, scores):
        if not self.hopefuls:
            return
        loser = min(self.hopefuls, key=lambda cand: scores[cand])
        self.losers.append(loser)
        self.hopefuls.remove(loser)
        self.rounds.append(Round(winners=None, loser=loser, scores=scores))
        for ballot in self.ballots:
            ballot.drop(loser)

    def show(self):
        print("Rounds:")
        for i, round in enumerate(self.rounds):
            print(f"Round {i + 1}:")
            for cand, score in sorted(round.scores.items(), key=lambda x: x[1], reverse=True):
                print(f"- {cand} - {score} - {score/len(self.ballots):.4%}")
            if round.winners is not None:
                print(f"Elected {len(round.winners)} candidates")
            if round.loser is not None:
                print(f"Eliminated {round.loser} and transferred votes")
        print("Results:")
        for i, winner in enumerate(self.winners):
            print(f"Seat {i + 1}: {winner} wins!")


def ballots_from_json(ballot_file: os.PathLike) -> tuple[list[Candidate], list[Ballot]]:
    data = json.loads(Path(ballot_file).read_text())
    candidates = data['candidates']

    ballots = []

    for datum in data['ballots']:
        count = datum.get('count', 1)
        ranking = datum['ranking']

        ballots.extend([Ballot(ranking.copy()) for _ in range(count)])

    return (candidates, ballots)


def party_plug(nparties, nseats, party_fractions) -> tuple[list[Candidate], list[Ballot]]:
    letters = string.ascii_uppercase
    if nparties > len(letters):
        raise ValueError(f"Max {len(letters)} parties")
    if len(party_fractions) != nparties:
        raise ValueError("Not every party has a fraction")
    parties = [party for party in letters[:nparties]]
    candidates = [f"{party}{i + 1}" for party in parties for i in range(nseats)]
    ballots = []
    party_fractions = [round(100*frac) for frac in party_fractions]
    for i, frac in enumerate(party_fractions):
        for _ in range(frac):
            ballots.append(Ballot([f"{parties[i]}{j + 1}" for j in range(nseats)]))
    return (candidates, ballots)


def main(ballot_file: str, seats: int = 1):
    candidates, ballots = ballots_from_json(ballot_file)
    election = Election(candidates, ballots, seats)
    election.run_election()
    election.show()


if __name__ == "__main__":
    typer.run(main)
