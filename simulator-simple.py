from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import matplotlib.pyplot as plt
from collections import defaultdict
import random


@dataclass
class sched_entity:
    # constants
    pid: int
    slice: int = 4000000
    weight: int = 1024

    # per era items -- used to calc lag
    runtime_since_placed: int = 0
    virt_time_placed : int = 0

    # per request items
    time_eligible: int = 0
    deadline: int = 3906
    time_gotten_in_slice: int = 0


@dataclass
class rq_struct:
    all_procs: list[sched_entity]
    virt_time: int = 0
    total_load: int = 0
    curr: Optional[sched_entity] = None

    timeline : list[scheduling_event] = field(default_factory=list)
    real_time : int = 0


@dataclass
class scheduling_event:
    pid: int
    type: str  # join, leave, run, new-req
    
    start_real_time: int
    start_virt_time: float
    end_real_time: int
    end_virt_time: float

    req_te: float
    req_dl: float


verbose : bool = True

def pick_eevdf(rq : rq_struct):
    next_se = max(rq.all_procs, key=lambda s: s.deadline)
    min_deadline : int = next_se.deadline

    for se in rq.all_procs:
        if se.deadline < min_deadline and entity_eligible(rq, se):
            min_deadline = se.deadline
            next_se = se
    
    rq.curr = next_se

    event = scheduling_event(rq.curr.pid, "pick", rq.real_time, rq.virt_time, rq.real_time, rq.virt_time, rq.curr.time_eligible, rq.curr.deadline)
    if verbose:
        print(event)
    rq.timeline.append(event)


def entity_eligible(rq : rq_struct, se : sched_entity) -> bool:
    return rq.virt_time >= se.time_eligible or lag(rq, se) > 0


def update_deadline(rq: rq_struct) -> bool:

    curr : sched_entity = rq.curr
    
    if curr.time_gotten_in_slice < curr.slice:
        return False

    curr.time_eligible = curr.deadline
    curr.deadline = curr.time_eligible + (curr.slice / curr.weight)


    event = scheduling_event(rq.curr.pid, "new-req", rq.real_time, rq.virt_time, rq.real_time, rq.virt_time, curr.time_eligible, curr.deadline)
    if verbose:
        print(event)
    rq.timeline.append(event)

    curr.time_gotten_in_slice = max(curr.time_gotten_in_slice - curr.slice, 0)

    return True

def run_curr(rq: rq_struct, amount_to_tick : int) -> bool:
    
    curr : sched_entity = rq.curr

    event = scheduling_event(rq.curr.pid, "run", rq.real_time, rq.virt_time, rq.real_time + amount_to_tick, 
                             rq.virt_time +  amount_to_tick / rq.total_load, curr.time_eligible, curr.deadline)
    if verbose:
        print(event)
    rq.timeline.append(event)

    curr.runtime_since_placed += amount_to_tick
    curr.time_gotten_in_slice += amount_to_tick

    rq.real_time += amount_to_tick

    rq.virt_time += amount_to_tick / rq.total_load 

    update_deadline(rq)
    


def lag(rq : rq_struct, se : sched_entity) -> float:
    
    ideal_service : int = se.weight * (rq.virt_time - se.virt_time_placed)
    real_service : int = se.runtime_since_placed

    return ideal_service - real_service


def place_entity(rq : rq_struct, se : sched_entity, lag : float):
    
    rq.all_procs.append(se)

    rq.total_load += se.weight

    og_virt_time = rq.virt_time

    if rq.total_load > 0:
        rq.virt_time -= lag / rq.total_load

    se.runtime_since_placed = 0

    se.time_eligible = rq.virt_time - (se.time_gotten_in_slice / se.weight)
    se.deadline = se.time_eligible + (se.slice / se.weight)

    event = scheduling_event(se.pid, "join", rq.real_time, og_virt_time, rq.real_time, 
                             rq.virt_time, se.time_eligible, se.deadline)
    if verbose:
        print(event)
    rq.timeline.append(event)
    


def dequeue_entity(rq : rq_struct, se : sched_entity) -> float:

    if (rq.curr == se):
        rq.curr = None
    
    og_virt_time = rq.virt_time

    rq.all_procs.remove(se)
    rq.total_load -= se.weight

    p_lag = lag(rq, se)

    if rq.total_load > 0:
        rq.virt_time += p_lag / rq.total_load

    event = scheduling_event(se.pid, "leave", rq.real_time, og_virt_time, rq.real_time, 
                             rq.virt_time, se.time_eligible, se.deadline)
    if verbose:
        print(event)
    rq.timeline.append(event)
    

    return p_lag




def main():

    rq = rq_struct([])

    linux_boot(rq)

    draw_timeline(rq.timeline)





# this is going to vaguely model linux boot behavior 
def linux_boot(rq : rq_struct):
    # setup:
    # all procs have default weight and slice
    p1 = sched_entity(1)
    p2 = sched_entity(2)
    p3 = sched_entity(3)
    p4 = sched_entity(4)


    total_num_ticks = 50
    curr_tick = 0

    place_entity(rq, p1, 0)
    place_entity(rq, p2, 0)
    place_entity(rq, p3, 0)
    place_entity(rq, p4, 0)

    pick_eevdf(rq)

    # num ticks to run total
    # TODO still need to do randomly joining and leaving
    while curr_tick < total_num_ticks:

        ticks_to_tick = random.randrange(1, 5)

        for _ in range(ticks_to_tick):
            run_curr(rq, 4000000)
        
        curr_tick += ticks_to_tick
        pick_eevdf(rq)









def draw_timeline(events):
    _, ax = plt.subplots(figsize=(12, 6))

    max_pid = max(event.pid for event in events)
    min_pid = min(event.pid for event in events)
    y_offset = (min_pid - 1) * 10  # Offset for the virtual time line

    bar_height = (max_pid * 10 + 10) / (max_pid + 1 - min_pid)

    for event in events:
        if event.type == 'run':
            ax.broken_barh([(event.start_real_time, event.end_real_time - event.start_real_time)],
                           (event.pid * 10, 5), facecolors=('tab:blue'))
            ax.text(event.start_real_time + (event.end_real_time - event.start_real_time) / 2,
                    event.pid * 10 + 2.5, f'P{event.pid}', ha='center', va='center', color='white')

        elif event.type == 'join':
            ax.annotate('↑', xy=(event.start_real_time, event.pid * 10), ha='center', color='green', fontsize=30)

        elif event.type == 'leave':
            ax.annotate('↓', xy=(event.start_real_time, event.pid * 10), ha='center', color='red', fontsize=30)
        
        elif event.type == 'pick':
            ax.axvline(x=event.start_real_time, color='gray', linestyle='--')

        elif event.type == 'new-req':
            ax.annotate('*', xy=(event.start_real_time, event.pid * 10), ha='center', color='orange', fontsize=20)
            ax.text(event.start_real_time - 1000000, event.pid * 10 - 0.3 , f'\n ({event.req_te}, \n {event.req_dl})', 
                    ha='left', va='center', fontsize=8, color='orange')

      
    virtual_times_by_real_time = defaultdict(list)
    for event in events:
        if event.start_virt_time not in virtual_times_by_real_time[event.start_real_time]:
            virtual_times_by_real_time[event.start_real_time].append(event.start_virt_time)
        if event.end_virt_time not in virtual_times_by_real_time[event.end_real_time]:
            virtual_times_by_real_time[event.end_real_time].append(event.end_virt_time)  
    
    # Plot the virtual time line
    ax.hlines(y=y_offset, xmin=0, xmax=max(event.end_real_time for event in events), color='black')
    
    # Plot the virtual times
    for real_time, virt_times in virtual_times_by_real_time.items():
        ax.vlines(x=real_time, ymin=y_offset - 1, ymax=y_offset + 1, color='black')  # Vertical tick
        for i, virt_time in enumerate(virt_times):
            ax.text(real_time, y_offset - 2 - i * 2, f'{virt_time:.1f}', ha='center', va='center', fontsize=8, color='black')
        
    # Main plot settings
    ax.set_ylim(y_offset - 15, max_pid * 10 + 10)

    max_rtime = max(event.end_real_time for event in events)
    ax.set_xlim(-0.05 * max_rtime, 1.05 * max_rtime)
    ax.set_xlabel('Real Time')

    ax.set_yticks([pid * 10 + 2.5 for pid in range(min_pid, max_pid + 1)])
    ax.set_yticklabels([f'P{pid}' for pid in range(min_pid, max_pid + 1)])

    plt.show()





if __name__=="__main__": 
    main() 




    


