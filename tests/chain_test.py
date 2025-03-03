from aip_agent.chain.chain import membase_chain


task_id = "task02271"
price = 100000
membase_chain.createTask(task_id, price)


agent_id = "alice"
membase_chain.register(agent_id)
membase_chain.joinTask(task_id, agent_id)

agent_id = "bob"
membase_chain.register(agent_id)
membase_chain.joinTask(task_id, agent_id)

membase_chain.finishTask(task_id, agent_id)
membase_chain.getTask(task_id)