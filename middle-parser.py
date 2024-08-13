from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class sched_entity:
    pid: int
    time_eligible: int = 0
    deadline: int = 3906
    vruntime: int = 0
    lag: int = 0
    slice: int = 4000000
    weight: int = 1024
    time_gotten_in_slice: int = 0


@dataclass
class rq:
    all_procs: List[sched_entity]
    virt_time: int = 0
    total_load: int = 0
    curr: Optional[sched_entity] = None



def print_rq(rq : rq):
    print("  virt_time : ", rq.virt_time)
    print("  total_load : ", rq.total_load)
    print("  curr : ", rq.curr)
    print("  procs: ")
    for s in rq.all_procs:
        print("    ", s)


def pick_eevdf(rq : rq):
    next_se = max(rq.all_procs, key=lambda s: s.deadline)
    min_deadline : int = next_se.deadline

    for se in rq.all_procs:
        if se.deadline < min_deadline and entity_eligible(rq, se):
            min_deadline = se.deadline
            next_se = se
    
    rq.curr = next_se


def entity_eligible(rq : rq, se : sched_entity) -> bool:
    return rq.virt_time >= se.time_eligible or ((se.weight * rq.virt_time - se.vruntime) > 0)


def update_deadline(rq: rq) -> bool:

    curr : sched_entity = rq.curr
    
    if curr.time_gotten_in_slice + 100 < curr.slice: # w/ added tolerance for being a little off
        return False

    curr.time_eligible = curr.deadline
    curr.deadline = curr.time_eligible + (curr.slice / curr.weight)
    curr.time_gotten_in_slice = max(curr.time_gotten_in_slice - curr.slice, 0)

    return True

def update_curr(rq: rq, amount_to_tick : int, pid: int) -> bool:

    # sometimes linux will deq and then imediately re-place the curr proc
    if rq.curr is None:
        for s in rq.all_procs:
            if s.pid == pid:
                rq.curr = s
    
    curr : sched_entity = rq.curr

    curr.vruntime += amount_to_tick
    curr.time_gotten_in_slice += amount_to_tick

    rq.virt_time += amount_to_tick / rq.total_load 

    resched : bool = update_deadline(rq)
    
    for s in rq.all_procs:
        update_lag(rq, s)

    return resched


def update_lag(rq : rq, se : sched_entity):
    
    ideal_service : int = se.weight * rq.virt_time
    real_service : int = se.vruntime

    se.lag = ideal_service - real_service


def place_entity(rq : rq, se : sched_entity, make_curr=False):
    
    rq.all_procs.append(se)

    if rq.total_load > 0:
        rq.virt_time -= se.lag / rq.total_load

    rq.total_load += se.weight

    se.vruntime = rq.virt_time * se.weight - se.lag

    se.time_eligible = rq.virt_time - (se.time_gotten_in_slice / se.weight)
    se.deadline = se.time_eligible + (se.slice / se.weight) 

    if make_curr:
        rq.curr = se


def dequeue_entity(rq : rq, se : sched_entity):

    if (rq.curr == se):
        rq.curr = None

    rq.all_procs.remove(se)
    rq.total_load -= se.weight

    update_lag(rq, se) 

    if rq.total_load > 0:
        print("updating virt time: vlag is ", se.lag, " and (new) total load is ", rq.total_load)
        rq.virt_time += se.lag / rq.total_load



def tick(rq : rq, amount_to_tick : int):
    resched : bool = update_curr(rq, amount_to_tick)

    if resched:
        # in reality, this is setting a flag
        pick_eevdf(rq)



def main():

    # parse input -- in each line, match to local function and run it, then check output match?
    ex_rq = rq([])

    parse_file("out.txt", ex_rq)

    print("\n \n END \n")

    print_rq(ex_rq)


    eligible = []
    for s in ex_rq.all_procs:
        if entity_eligible(ex_rq, s):
            eligible.append(s.pid)
    print("pids eligible: ", eligible)














def parse_file(file_path, rq : rq):

    with open(file_path, 'r') as file:
        for line in file:
            if 'update_curr' in line:
                start_index = line.find('delta exec: ') + len('delta exec: ')
                end_index = line.find(',', start_index)
                if end_index == -1:
                    end_index = len(line)
                vrt_value = line[start_index:end_index].strip()

                start_index = line.find('update_curr ') + len('update_curr ')
                end_index = line.find(':', start_index)
                if end_index == -1:
                    end_index = len(line)
                pid_value = line[start_index:end_index].strip()

                start_index = line.find('virt time: ') + len('virt time: ')
                end_index = line.find('\n', start_index)
                if end_index == -1:
                    end_index = len(line)
                new_vrt_value = line[start_index:end_index].strip()
                vals = new_vrt_value.split(".")
                actual_vrt_val = int(vals[0]) + (int(vals[1]) / (2**16))

                update_curr(rq, int(vrt_value), int(pid_value))
                print("update ", rq.curr.pid, " by ", vrt_value, " -- V is now ", rq.virt_time, " so curr diff is ", actual_vrt_val - rq.virt_time, " curr's te is now ", rq.curr.time_eligible)
            if 'pick_next_entity' in line:
                print("pick")
                start_index = line.find('new_curr: ') + len('new_curr: ')
                end_index = line.find(' ', start_index)
                if end_index == -1:
                    end_index = len(line)
                new_pid = line[start_index:end_index].strip()
                pick_eevdf(rq)
                if (rq.curr.pid != int(new_pid)):
                    print("ERROR - diff in choice -- lnx: ", new_pid, ", this program: ", rq.curr.pid)
                    for s in rq.all_procs:
                        if s.pid == int(new_pid):
                            rq.curr = s
            if 'place_entity' in line:
                start_index = line.find('placing se: ') + len('placing se: ')
                end_index = line.find(', ', start_index)
                if end_index == -1: 
                    end_index = len(line)
                new_pid = line[start_index:end_index].strip()

                start_index = line.find('weight: ') + len('weight: ')
                end_index = line.find(', ', start_index)
                if end_index == -1: 
                    end_index = len(line)
                s_weight = line[start_index:end_index].strip()

                start_index = line.find('t_g_i_s: ') + len('t_g_i_s: ')
                end_index = line.find('\n ', start_index)
                if end_index == -1: 
                    end_index = len(line)
                t_g_i_s = line[start_index:end_index].strip()
                
                start_index = line.find('vlag: ') + len('vlag: ')
                end_index = line.find(', ', start_index)
                if end_index == -1: 
                    end_index = len(line)
                lag = line[start_index:end_index].strip()

                start_index = line.find('new virt_time: ') + len('new virt_time: ')
                end_index = line.find(', ', start_index)
                if end_index == -1: 
                    end_index = len(line)
                lnx_virt_time_vals = line[start_index:end_index].strip().split(".")

                print("vvvvvvvvvvvvvv")
                print("before: ")
                print_rq(rq)
                print("====> place")

                new_se = sched_entity(int(new_pid), lag=int(lag), weight=int(s_weight), time_gotten_in_slice=int(t_g_i_s))
                print("placing se: ", new_se)
                if 'RE-' in line:
                    place_entity(rq, new_se, True)
                else:
                    place_entity(rq, new_se)
                actual_vrt_val = int(lnx_virt_time_vals[0]) + (int(lnx_virt_time_vals[1]) / (2**16))
                print("after: DIFF: ", actual_vrt_val - rq.virt_time)
                print_rq(rq)
                print("^^^^^^^^^^^^^^^^^^^^")
            if 'dequeue_entity' in line:
                start_index = line.find(' task being dequeued ') + len(' task being dequeued ')
                end_index = line.find(' ', start_index)
                if end_index == -1: 
                    end_index = len(line)
                pid = line[start_index:end_index].strip()

                start_index = line.find('new virt_time: ') + len('new virt_time: ')
                end_index = line.find(' ', start_index)
                if end_index == -1: 
                    end_index = len(line)
                lnx_virt_time_vals = line[start_index:end_index].strip().split(".")
                actual_vrt_val = int(lnx_virt_time_vals[0]) + (int(lnx_virt_time_vals[1]) / (2**16))

                print("vvvvvvvvvvvvvv")
                print("before: ")
                print_rq(rq)
                print("====> dequeue")

                for s in rq.all_procs:
                    if s.pid == int(pid):
                        update_lag(rq, s)
                        dequeue_entity(rq, s)
                        print("after: DIFF: ", actual_vrt_val - rq.virt_time)
                        print_rq(rq)
                        print("^^^^^^^^^^^^^^^^^^^^")
                        continue



if __name__=="__main__": 
    main() 

