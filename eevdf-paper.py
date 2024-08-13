
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class sched_entity:
    pid: int
    lag: int
    weight: int
    req: request
    # I added for lag tracking
    init_vt: int
    total_time : int

# they put this into a tree structure, the infrastructure for which I am ignoring for now
@dataclass
class request:
    ve: int
    vd: int = 0


virtual_time : int
total_weight: int

quantum_size: int


def place_entity(client: sched_entity):

    # update total weight of all active clients 
    total_weight += client.weight

    # update virtual time according to client lag
    virtual_time = get_current_vt() - client.lag/total_weight

    # issue request
    client.init_vt = virtual_time
    client.req.ve = virtual_time
    client.req.vd = client.req.ve + quantum_size/client.weight

    # insert request into tree
    # TODO ignoring for now - interaction with req tree


def dequeue_entity(client: sched_entity):
    
    # update total weight of all active clients 
    total_weight -= client.weight

    # update virtual time according to client lag
    virtual_time = get_current_vt() + client.lag/total_weight
    
    # delete request from tree
    # TODO ignoring for now - interaction with req tree



def change_weight(client: sched_entity, new_weight: int):
    
    # partial update virtual time according to client lag
    virtual_time = get_current_vt() + client.lag/(total_weight - client.weight)
    
    # update total weight of all active clients
    total_weight += new_weight - client.weight
    
    # update client's weight
    client.weight = new_weight

    # update virtual time
    virtual_time -= client.lag/total_weight


def EEVDF_dispatch(): 
    used: int

    # get eligible request with earliest virtual dead line 
    # TODO ignoring for now - interaction with req tree
    client : sched_entity
    
    # allocate resource to client with earliest eligible virtual dead line
    used = allocate(client)
    
    # update client's lag
    update_lag(client, used)

    # current request has been fulfilled; delete it 
    # TODO ignoring for now - interaction with req tree

    # issue new request 
    client.req.ve += used/client.weight
    client.req.vd = client.req.ve + quantum_size/client.weight

    # TODO added by Hannah
    virtual_time += used / total_weight
    
    # insert new request into tree
    # TODO ignoring for now - interaction with req tree
    


# funcs created by me
def update_lag(client: sched_entity, used : int):
    
    ideal_service_time = client.weight * (get_current_vt() - client.init_vt)
    client.total_time += used
    
    client.lag = ideal_service_time - client.total_time


def get_current_vt() -> int:
    return virtual_time


def allocate():
    pass