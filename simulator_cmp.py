import simulator_simple
import simulator_avg
from random import uniform, randrange


simulator_avg.verbose = True
simulator_simple.verbose = True



def main():
    # compare their behaviors?
    rq_simple = simulator_simple.rq_struct([])
    rq_avg = simulator_avg.rq_struct([])

    random_mixed(rq_simple, rq_avg)

    print("done w/ one")

    rq_simple = simulator_simple.rq_struct([])
    rq_avg = simulator_avg.rq_struct([])

    random_short(rq_simple, rq_avg)


def random_mixed(rq_simple : simulator_simple.rq_struct, rq_avg : simulator_avg.rq_struct):

    # all procs have default weight and slice
    p1_simple = simulator_simple.sched_entity(1, slice=80000000) # 80 ms
    p1_avg = simulator_avg.sched_entity(1, slice=80000000) # 80 ms
    p2_simple = simulator_simple.sched_entity(2)
    p2_avg = simulator_avg.sched_entity(2)

    total_num_ticks = 500

    simulator_simple.place_entity(rq_simple, p1_simple, 0)
    simulator_avg.place_entity(rq_avg, p1_avg, 0)
    simulator_simple.place_entity(rq_simple, p2_simple, 0)
    simulator_avg.place_entity(rq_avg, p2_avg, 0)

    simulator_simple.pick_eevdf(rq_simple)
    simulator_avg.pick_eevdf(rq_avg)

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
                simulator_simple.place_entity(rq_simple, p1_simple, p1_lag_simple)
                simulator_avg.place_entity(rq_avg, p1_avg, p1_lag_avg)
                p1_removed = False
            else:
                print("adding")
                simulator_simple.place_entity(rq_simple, p2_simple, p2_lag_simple)
                simulator_avg.place_entity(rq_avg, p2_avg, p2_lag_avg)
                p2_removed = False
        elif p1_removed:
            if uniform(0, 1) > 0.5:
                print("adding")
                simulator_simple.place_entity(rq_simple, p1_simple, p1_lag_simple)
                simulator_avg.place_entity(rq_avg, p1_avg, p1_lag_avg)
                p1_removed = False
        elif p2_removed:
            if uniform(0, 1) > 0.5:
                print("adding")
                simulator_simple.place_entity(rq_simple, p2_simple, p2_lag_simple)
                simulator_avg.place_entity(rq_avg, p2_avg, p2_lag_avg)
                p2_removed = False


        simulator_simple.pick_eevdf(rq_simple)
        simulator_avg.pick_eevdf(rq_avg)
        if rq_simple.curr.pid != rq_avg.curr.pid:
            print("DIFF")

        ticks_to_tick = randrange(1, 5)
        for _ in range(ticks_to_tick):
            simulator_simple.run_curr(rq_simple, 4000000)
            simulator_avg.run_curr(rq_avg, 4000000)
        
        if uniform(0, 1) > 0.9:
            if p1_removed and not p2_removed:
                print("removing")
                p2_lag_simple = simulator_simple.dequeue_entity(rq_simple, p2_simple)
                p2_lag_avg = simulator_avg.dequeue_entity(rq_avg, p2_avg)
                p2_removed = True
            elif not p1_removed and p2_removed:
                print("removing")
                p1_lag_simple = simulator_simple.dequeue_entity(rq_simple, p1_simple)
                p1_lag_avg = simulator_avg.dequeue_entity(rq_avg, p1_avg)
                p1_removed = True
            elif not p1_removed and not p2_removed:
                if randrange(0, 1) > 0.5:
                    print("removing")
                    p2_lag_simple = simulator_simple.dequeue_entity(rq_simple, p2_simple)
                    p2_lag_avg = simulator_avg.dequeue_entity(rq_avg, p2_avg)
                    p2_removed = True
                else:
                    print("removing")
                    p1_lag_simple = simulator_simple.dequeue_entity(rq_simple, p1_simple)
                    p1_lag_avg = simulator_avg.dequeue_entity(rq_avg, p1_avg)
                    p1_removed = True

        curr_tick += ticks_to_tick




def random_short(rq_simple : simulator_simple.rq_struct, rq_avg : simulator_avg.rq_struct):

    # all procs have default weight and slice
    p1_simple = simulator_simple.sched_entity(1)
    p1_avg = simulator_avg.sched_entity(1)
    p2_simple = simulator_simple.sched_entity(2)
    p2_avg = simulator_avg.sched_entity(2)
    p3_simple = simulator_simple.sched_entity(3)
    p3_avg = simulator_avg.sched_entity(3)
    p4_simple = simulator_simple.sched_entity(4)
    p4_avg = simulator_avg.sched_entity(4)

    total_num_ticks = 50

    simulator_simple.place_entity(rq_simple, p1_simple, 0)
    simulator_avg.place_entity(rq_avg, p1_avg, 0)
    simulator_simple.place_entity(rq_simple, p2_simple, 0)
    simulator_avg.place_entity(rq_avg, p2_avg, 0)
    simulator_simple.place_entity(rq_simple, p3_simple, 0)
    simulator_avg.place_entity(rq_avg, p3_avg, 0)
    simulator_simple.place_entity(rq_simple, p4_simple, 0)
    simulator_avg.place_entity(rq_avg, p4_avg, 0)

    simulator_simple.pick_eevdf(rq_simple)
    simulator_avg.pick_eevdf(rq_avg)

    # TODO still need to do randomly joining and leaving
    curr_tick = 0
    while curr_tick < total_num_ticks:

        ticks_to_tick = randrange(1, 5)

        for _ in range(ticks_to_tick):
            simulator_simple.run_curr(rq_simple, 4000000)
            simulator_avg.run_curr(rq_avg, 4000000)
        
        curr_tick += ticks_to_tick
        simulator_simple.pick_eevdf(rq_simple)
        simulator_avg.pick_eevdf(rq_avg)

        if rq_simple.curr.pid != rq_avg.curr.pid:
            print("DIFF")




if __name__=="__main__": 
    main() 

