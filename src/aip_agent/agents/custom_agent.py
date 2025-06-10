from autogen_core import (
    MessageContext,
    RoutedAgent,
    message_handler,
)

from aip_agent.workflows.llm.augmented_llm import (
    AugmentedLLM, 
    RequestParams
)

from aip_agent.message.message import InteractionMessage
from membase.memory.message import Message
from membase.memory.multi_memory import MultiMemory

class CallbackAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        llm: AugmentedLLM,
        memory: MultiMemory,
    ) -> None:
        super().__init__(description=description)
        self._memory = memory
        self._llm = llm
    
    def verify_auth(self, message: InteractionMessage, ctx: MessageContext) -> bool:
        return True

    @message_handler
    async def handle_message(self, message: InteractionMessage, ctx: MessageContext) -> InteractionMessage:
        #print(f"receive message from {message.source} with content: {message.content}")
        if not self.verify_auth(message, ctx):
            return InteractionMessage(
                action="response",
                content="Unauthorized message",
                source=self.id.type
            )

        if message.action == "heartbeat":
            return InteractionMessage(
                action="response",
                content="ok"
            )
    
        #print(f"{message.source} {ctx.sender}")
        memory = self._memory.get_memory()
        memory.add(Message(content=message.content, name=self.id.type, role="user", metadata={"source": message.source}))
        try:
            response = await self._llm.generate_str(
                    message.content,
                    request_params=RequestParams(
                        use_history=False
                    )
                )
        except Exception as e:
            response = "I'm sorry, I couldn't generate a response to that message due to an error:" + str(e)
        memory.add(Message(content=response, name=self.id.type, role="assistant", metadata={"source": message.source}))
        return InteractionMessage(
            action="response",
            content=response,
            source=self.id.type
        )