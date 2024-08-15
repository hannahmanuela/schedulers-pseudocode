from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import matplotlib.pyplot as plt
from collections import defaultdict
from random import randrange, uniform


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

    cls : str = "simple"


verbose : bool = True


def print_rq(rq : rq_struct):
    print(f"virt_time: {rq.virt_time:.1f}")
    print("  total_load : ", rq.total_load)
    print("  curr : ", rq.curr)
    print("  procs: ")
    for s in rq.all_procs:
        print_se(rq, s)

def print_se(rq : rq_struct, se : sched_entity):
    print(f"   pid: {se.pid}, weight: {se.weight}, te: {se.time_eligible:.1f}, dl: {se.deadline:.1f}, time_gotten_in_slice: {se.time_gotten_in_slice}, lag: {get_lag(rq, se):.1f}, virt_time_placed: {se.virt_time_placed}, runtime_since_placed: {se.runtime_since_placed:.1f}")




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
        print("simple - sum: ", sum([get_lag(rq, s) for s in rq.all_procs]))
    rq.timeline.append(event)


def entity_eligible(rq : rq_struct, se : sched_entity) -> bool:
    return rq.virt_time >= se.time_eligible or get_lag(rq, se) > 0


def update_deadline(rq: rq_struct) -> bool:

    curr : sched_entity = rq.curr
    
    if curr.time_gotten_in_slice < curr.slice:
        return False

    curr.time_eligible = curr.deadline
    curr.deadline = curr.time_eligible + (curr.slice / curr.weight)


    event = scheduling_event(rq.curr.pid, "new-req", rq.real_time, rq.virt_time, rq.real_time, rq.virt_time, curr.time_eligible, curr.deadline)
    if verbose:
        print(event)
        print("simple - sum: ", sum([get_lag(rq, s) for s in rq.all_procs]))
    rq.timeline.append(event)

    curr.time_gotten_in_slice = max(curr.time_gotten_in_slice - curr.slice, 0)

    return True

def run_curr(rq: rq_struct, amount_to_tick : int, pid : int = None) -> bool:

    # sometimes linux will deq and then imediately re-place the curr proc
    # this should only be the case when running from linux output, only set the value there
    if rq.curr is None and pid is not None:
        for s in rq.all_procs:
            if s.pid == pid:
                rq.curr = s
    
    curr : sched_entity = rq.curr

    event = scheduling_event(rq.curr.pid, "run", rq.real_time, rq.virt_time, rq.real_time + amount_to_tick, 
                             rq.virt_time +  amount_to_tick / rq.total_load, curr.time_eligible, curr.deadline)
    if verbose:
        print(event)
        print("simple - sum: ", sum([get_lag(rq, s) for s in rq.all_procs]))
    rq.timeline.append(event)

    curr.runtime_since_placed += amount_to_tick
    curr.time_gotten_in_slice += amount_to_tick

    rq.real_time += amount_to_tick

    rq.virt_time += amount_to_tick / rq.total_load 

    update_deadline(rq)
    


def get_lag(rq : rq_struct, se : sched_entity) -> float:
    
    ideal_service : int = se.weight * (rq.virt_time - se.virt_time_placed)
    real_service : int = se.runtime_since_placed

    return ideal_service - real_service


def place_entity(rq : rq_struct, se : sched_entity, lag : float):
    
    rq.all_procs.append(se)

    rq.total_load += se.weight

    og_virt_time = rq.virt_time

    se.runtime_since_placed = 0
    se.virt_time_placed = rq.virt_time - (lag / se.weight)

    if rq.total_load > 0:
        rq.virt_time -= lag / rq.total_load

    se.time_eligible = rq.virt_time - (se.time_gotten_in_slice / se.weight)
    se.deadline = se.time_eligible + (se.slice / se.weight)

    event = scheduling_event(se.pid, "join", rq.real_time, og_virt_time, rq.real_time, 
                             rq.virt_time, se.time_eligible, se.deadline)
    if verbose:
        print("placing pid ", se.pid, " w/ lag ", lag)
        print(event)
        print("simple - sum: ", sum([get_lag(rq, s) for s in rq.all_procs]))
        for s in rq.all_procs:
            print_se(rq, s)
    rq.timeline.append(event)
    


def dequeue_entity(rq : rq_struct, se : sched_entity) -> float:

    if (rq.curr == se):
        rq.curr = None
    
    og_virt_time = rq.virt_time

    rq.all_procs.remove(se)
    rq.total_load -= se.weight

    p_lag = get_lag(rq, se)

    if rq.total_load > 0:
        rq.virt_time += p_lag / rq.total_load

    event = scheduling_event(se.pid, "leave", rq.real_time, og_virt_time, rq.real_time, 
                             rq.virt_time, se.time_eligible, se.deadline)
    if verbose:
        print(event)
        print("simple - sum: ", sum([get_lag(rq, s) for s in rq.all_procs]))
    rq.timeline.append(event)
    

    return p_lag




def main():

    rq = rq_struct([])

    random_mixed(rq)

    # print_rq(rq)

    draw_timeline(rq.timeline)



def random_long(rq : rq_struct):

    # all procs have default weight and slice
    p1 = sched_entity(1, slice=80000000) # 80 ms
    p2 = sched_entity(2, slice=60000000) # 60 ms

    total_num_ticks = 50

    place_entity(rq, p1, 0)
    place_entity(rq, p2, 0)

    pick_eevdf(rq)

    # TODO still need to do randomly joining and leaving
    curr_tick = 0
    while curr_tick < total_num_ticks:

        ticks_to_tick = random.randrange(1, 5)

        for _ in range(ticks_to_tick):
            run_curr(rq, 4000000)
        
        curr_tick += ticks_to_tick
        pick_eevdf(rq)


def random_mixed(rq_simple : rq_struct):

    # all procs have default weight and slice
    p1_simple = sched_entity(1, slice=80000000) # 80 ms
    p2_simple = sched_entity(2)

    total_num_ticks = 50

    place_entity(rq_simple, p1_simple, 0)
    place_entity(rq_simple, p2_simple, 0)

    pick_eevdf(rq_simple)

    p1_removed = False
    p1_lag_simple = 0
    p1_lag_avg = 0
    p2_removed = False
    p2_lag_simple = 0
    p2_lag_avg = 0


    # TODO still need to do randomly joining and leaving
    curr_tick = 0
    while curr_tick < total_num_ticks:

        if p1_removed and p2_removed:
            if uniform(0, 1) > 0.5:
                print("adding")
                place_entity(rq_simple, p1_simple, p1_lag_simple)
                p1_removed = False
            else:
                print("adding")
                place_entity(rq_simple, p2_simple, p2_lag_simple)
                p2_removed = False
        elif p1_removed:
            if uniform(0, 1) > 0.5:
                print("adding")
                place_entity(rq_simple, p1_simple, p1_lag_simple)
                p1_removed = False
        elif p2_removed:
            if uniform(0, 1) > 0.5:
                print("adding")
                place_entity(rq_simple, p2_simple, p2_lag_simple)
                p2_removed = False


        pick_eevdf(rq_simple)

        ticks_to_tick = randrange(1, 5)
        for _ in range(ticks_to_tick):
            run_curr(rq_simple, 4000000)
        
        if uniform(0, 1) > 0.9:
            if p1_removed and not p2_removed:
                print("removing")
                p2_lag_simple = dequeue_entity(rq_simple, p2_simple)
                p2_removed = True
            elif not p1_removed and p2_removed:
                print("removing")
                p1_lag_simple = dequeue_entity(rq_simple, p1_simple)
                p1_removed = True
            elif not p1_removed and not p2_removed:
                if randrange(0, 1) > 0.5:
                    print("removing")
                    p2_lag_simple = dequeue_entity(rq_simple, p2_simple)
                    p2_removed = True
                else:
                    print("removing")
                    p1_lag_simple = dequeue_entity(rq_simple, p1_simple)
                    p1_removed = True

        curr_tick += ticks_to_tick



def random_short(rq : rq_struct):

    # all procs have default weight and slice
    p1 = sched_entity(1)
    p2 = sched_entity(2)
    p3 = sched_entity(3)
    p4 = sched_entity(4)

    total_num_ticks = 50

    place_entity(rq, p1, 0)
    place_entity(rq, p2, 0)
    place_entity(rq, p3, 0)
    place_entity(rq, p4, 0)

    pick_eevdf(rq)

    # TODO still need to do randomly joining and leaving
    curr_tick = 0
    while curr_tick < total_num_ticks:

        ticks_to_tick = randrange(1, 5)

        for _ in range(ticks_to_tick):
            run_curr(rq, 4000000)
        
        curr_tick += ticks_to_tick
        pick_eevdf(rq)




def run_from_linux_output_file(rq : rq_struct):

    pid_to_se_and_lag = {}

    with open('out.txt', 'r') as file:
        for line in file:
            if 'update_curr' in line:
                time_run = get_val('delta exec: ', ',', line)
                pid_value = get_val('update_curr ', ':', line)
                run_curr(rq, int(time_run), int(pid_value))

            if 'pick_next_entity' in line:
                new_pid = get_val('new_curr: ', ' ', line)
                pick_eevdf(rq)

                if (rq.curr.pid != int(new_pid)):
                    print("ERROR - diff in choice -- lnx: ", new_pid, ", this program: ", rq.curr.pid)
                    for s in rq.all_procs:
                        if s.pid == int(new_pid):
                            rq.curr = s
    
            if 'place_entity' in line:
                new_pid = get_val('placing se: ', ', ', line)
                s_weight = get_val('weight: ', ', ', line)

                if new_pid in pid_to_se_and_lag:
                    se_to_add = pid_to_se_and_lag[new_pid][0]
                    lag = pid_to_se_and_lag[new_pid][1]
                    pid_to_se_and_lag.__delitem__(new_pid)
                else:
                    se_to_add = sched_entity(int(new_pid), weight=int(s_weight))
                    lag = 0

                place_entity(rq, se_to_add, lag)

            if 'dequeue_entity' in line:
                pid = get_val(' task being dequeued ', ', ', line)

                for s in rq.all_procs:
                    if s.pid == int(pid):
                        lag = dequeue_entity(rq, s)
                        pid_to_se_and_lag[s.pid] = (s, lag)
                        break



def get_val(start : str, end : str, line : str)->str:
    
    start_index = line.find(start) + len(start)
    end_index = line.find(end, start_index)
    if end_index == -1: 
        end_index = len(line)
    return line[start_index:end_index].strip()










def draw_timeline(events, simple : bool = False):
    _, ax = plt.subplots(figsize=(12, 6))

    max_pid = max(event.pid for event in events)
    min_pid = min(event.pid for event in events)
    y_offset = (min_pid - 1) * 10  # Offset for the virtual time line

    for event in events:
        if event.type == 'run':
            ax.broken_barh([(event.start_real_time, event.end_real_time - event.start_real_time)],
                           (event.pid * 10, 5), facecolors=('tab:blue'))
            if not simple:
                ax.text(event.start_real_time + (event.end_real_time - event.start_real_time) / 2, 
                        event.pid * 10 + 2.5, f'P{event.pid}', ha='center', va='center', color='white')

        elif event.type == 'join':
            if not simple:
                ax.annotate('↑', xy=(event.start_real_time, event.pid * 10), ha='center', color='green', fontsize=30)
            else:
                ax.annotate('↑', xy=(event.start_real_time, event.pid * 10), ha='center', color='green')

        elif event.type == 'leave':
            if not simple:
                ax.annotate('↓', xy=(event.start_real_time, event.pid * 10), ha='center', color='red', fontsize=30)
            else:
                ax.annotate('↓', xy=(event.start_real_time, event.pid * 10), ha='center', color='red')
        
        elif event.type == 'pick' and not simple:
            ax.axvline(x=event.start_real_time, color='gray', linestyle='--')

        elif event.type == 'new-req' and not simple:
            ax.annotate('*', xy=(event.start_real_time, event.pid * 10), ha='center', color='orange', fontsize=20)
            ax.text(event.start_real_time - 1000000, event.pid * 10 - 0.3 , f'\n ({event.req_te}, \n {event.req_dl})', 
                    ha='left', va='center', fontsize=8, color='orange')

    if not simple:
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




    


