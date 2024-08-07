from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class sched_entity:
    pid: int
    deadline: int = 3906
    vruntime: int = 0
    vlag: int = 0
    slice: int = 4000000
    weight: int = 1024
    rel_deadline : int


@dataclass
class rq:
    all_procs: List[sched_entity]
    avg_vruntime : int = 0  # as a diff to min_vrt, and weighted
    min_vruntime : int = 0
    total_load: int = 0
    curr: Optional[sched_entity] = None


# details left out:
# - curr is removed from the rq when it is running
# a whole bunch of other stuff eg stats tracking for cgroups etc


PLACE_REL_DEADLINE: bool
PLACE_LAG: bool



# this only very vaguely does the same thing as the tree traversal
def pick_eevdf(rq : rq):
    next_se = max(rq.all_procs, key=lambda s: s.deadline)
    min_deadline : int = next_se.deadline

    for se in rq.all_procs:
        if se.deadline < min_deadline and entity_eligible(rq, se):
            min_deadline = se.deadline
            next_se = se
    
    rq.curr = next_se


def entity_eligible(rq : rq, se : sched_entity) -> bool:

    avg = rq.avg_vruntime
    load = rq.total_load
        
    return avg >= (se.vruntime - rq.min_vruntime) * load;


def update_deadline(rq: rq, se: sched_entity) -> bool:
    
    if (se.vruntime - se.deadline) < 0:
        return False
    
    se.deadline = se.vruntime + se.slice

    return True


def update_lag(rq : rq, se : sched_entity):
    
    lag = avg_vrt(rq) - se.vruntime
    limit = 2 * se.slice
    # clamp lag between -limit and limit
    se.vlag = max(-limit, min(lag, limit))
    

def avg_vrt(rq : rq) -> int:

    avg = rq.avg_vruntime

    if (avg < 0):
        avg -= (rq.total_load - 1)
        avg = avg // rq.total_load

    return avg + rq.min_vruntime


def avg_vruntime_add(rq : rq, se : sched_entity):
    rq.avg_vruntime += (se.vruntime - rq.min_vruntime) * se.weight
    rq.total_load += se.weight

def avg_vruntime_sub(rq : rq, se : sched_entity):
    rq.avg_vruntime -= (se.vruntime - rq.min_vruntime) * se.weight
    rq.total_load -= se.weight

def avg_vruntime_update(rq : rq, delta : int):
    rq.avg_vruntime -= rq.total_load * delta

def update_min_vrt(rq : rq):
    min_vrt = min(rq.all_procs, key=lambda s: s.vruntime)
    delta = min_vrt - rq.min_vruntime
    if delta > 0:
        avg_vruntime_update(rq, delta)
        rq.min_vruntime = min_vrt


def dequeue_entity(rq : rq, se : sched_entity):

    update_lag(rq, se)

    if PLACE_REL_DEADLINE:
        se.deadline -= se.vruntime
        se.rel_deadline = 1
    
    avg_vruntime_sub(se)

    update_min_vrt(rq)
    
    # removed from tree somewhere else, included here for completeness' sake
    rq.all_procs.remove(se)


def enqueue_entity(rq: rq, se : sched_entity):

    update_curr(rq, )

    place_entity(rq, se)

    avg_vruntime_add(rq, se)


def place_entity(rq : rq, se : sched_entity):
    
    vruntime = avg_vrt(rq)
    lag = 0

    if (PLACE_LAG):
        lag = se.vlag
        lag = lag * (rq.total_load + se.weight)
        lag = lag // rq.total_load
    
    se.vruntime = vruntime - lag

    if (PLACE_REL_DEADLINE):
        se.deadline += se.vruntime
        se.rel_deadline = 0
        return

    se.deadline = se.vruntime + se.slice       

    # this happens somewhere else, is here for completeness' sake
    rq.all_procs.append(se)


def update_curr(rq: rq, amount_to_tick : int) -> bool:

    curr = rq.curr

    curr.vruntime += amount_to_tick

    resched = update_deadline(rq, curr)

    update_min_vrt(rq)

    # if resched, sets flag