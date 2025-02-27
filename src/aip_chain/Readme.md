# aip chain

## task

- bnb testnet

```shell
export MEMBASE_ID="<agent uuid>"
export MEMBASE_ACCOUNT="<agent account>"
export MEMBASE_SECRET_KEY="<agent secret key>"
```

```python

from aip_chain.chain import membase_chain

# register task with id and price<minimal staking>
# as task owner
task_id = "task0227"
price = 100000
membase_chain.createTask(task_id, price)

# another one
# join this task, and staking
agent_id = "alice"
membase_chain.register(agent_id)
membase_chain.joinTask(task_id, agent_id)


# another one
agent_id = "bob"
membase_chain.register(agent_id)
membase_chain.joinTask(task_id, agent_id)


# finish task
# 95% belongs to winner: agent_id, 5% belongs to task owner
# call by task owner
membase_chain.finishTask(task_id, agent_id)

# show info
membase_chain.getTask(task_id)
```
