from autogen_core import (
    MessageContext,
    RoutedAgent,
    message_handler,
)

from aip_agent.workflows.llm.augmented_llm import AugmentedLLM

from aip_agent.message.message import InteractionMessage
from membase.memory.message import Message
from membase.memory.memory import MemoryBase

class CallbackAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        llm: AugmentedLLM,
        memory: MemoryBase,
    ) -> None:
        super().__init__(description=description)
        self._memory = memory
        self._llm = llm
    
    def verify_auth(self, message: InteractionMessage, ctx: MessageContext) -> bool:
        return True

    @message_handler
    async def handle_message(self, message: InteractionMessage, ctx: MessageContext) -> InteractionMessage:
        if not self.verify_auth(message, ctx):
            return InteractionMessage(
                action="response",
                content="Unauthorized message",
                source=self.id.type
            )

        print(f"{message.source} {ctx.sender}")
        self._memory.add(Message(content=message.content, name=message.source, role="user"))
        try:
            response = await self._llm.generate_str(message.content)
        except Exception as e:
            response = "I'm sorry, I couldn't generate a response to that message."
        self._memory.add(Message(content=response, name=self.id, role="assistant"))
        return InteractionMessage(
            action="response",
            content=response,
            source=self.id.type
        )