"""Reference model of the timing scan (ws2/timer_theorem.md section 1), in plain Python.

It is a second implementation of the rules, independent of ld_converter.cpp, used to predict the exact
worst-case response time of an L1 case by exhaustive search over input and delta sequences.
"""
from collections import deque


def adv(et, pt, d):
    return et + min(d, pt - et) if et < pt else et


def ton(s, inp, d, pt):
    et, q, prev = s
    held = inp and prev
    et2 = adv(et, pt, d) if held else 0
    return (et2, held and et2 >= pt, inp)


def tof(s, inp, d, pt):
    et, q, prev = s
    if inp:
        return (0, True, inp)
    if q and not prev:
        et2 = adv(et, pt, d)
        return (et2, et2 < pt, inp)
    return (et, q, inp)


def tp(s, inp, d, pt):
    et, q, prev = s
    if q:
        et2 = adv(et, pt, d)
        return (et2, et2 < pt, inp)
    if inp and not prev:
        return (0, True, inp)
    return (et, q, inp)


STEP = {"TON": ton, "TOF": tof, "TP": tp}
START = (0, False, False)


def observe(kind, states):
    """(trigger, response) of the monitor at the end of a scan, from the timer states."""
    q_last = states[-1][1]
    if kind == "TOF":
        return (not states[0][2], not q_last)  # trigger: IN low; response: Q low
    if kind == "TP":
        return (q_last, not q_last)  # trigger: pulse on; response: pulse off
    return (states[0][2], q_last)  # TON and cascade: IN high until Q


def scan(timers, states, inp, d):
    """One scan: timers run top to bottom, each timer's IN being the previous timer's Q."""
    out, cur = [], inp
    for (k, pt), s in zip(timers, states):
        s2 = STEP[k](s, cur, d, pt)
        out.append(s2)
        cur = s2[1]
    return tuple(out)


def worst_case(kind, timers, tmin, tmax, bound=100000):
    """Largest monitor value over all input and delta sequences, and the fewest scans that reach it.

    Returns (max_c, scans) or (None, None) when the monitor is unbounded.
    """
    init = tuple(START for _ in timers)
    best = {init: (0, 0)}  # state -> (c, scans)
    queue = deque([init])
    top = (0, 0)
    while queue:
        st = queue.popleft()
        c, n = best[st]
        for inp in (False, True):
            for d in range(tmin, tmax + 1):
                nxt = scan(timers, st, inp, d)
                trig, resp = observe(kind, nxt)
                c2 = c + d if (trig and not resp) else 0
                if c2 > bound:
                    return None, None
                old = best.get(nxt)
                if old is None or c2 > old[0] or (c2 == old[0] and n + 1 < old[1]):
                    best[nxt] = (c2, n + 1)
                    queue.append(nxt)
                    if c2 > top[0] or (c2 == top[0] and n + 1 < top[1]):
                        top = (c2, n + 1)
    return top


def closed_form(pt, tmin, tmax):
    """Tmax plus the largest sum of deltas below PT (valid for one timer; checked against the search)."""
    reach = {0}
    for s in range(1, pt):
        if any((s - d) in reach for d in range(tmin, tmax + 1)):
            reach.add(s)
    return tmax + max(reach)
