from typing import List, Optional, TYPE_CHECKING

from aip_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from aip_agent.workflows.intent_classifier.intent_classifier_base import Intent
from aip_agent.workflows.intent_classifier.intent_classifier_llm import (
    LLMIntentClassifier,
)

if TYPE_CHECKING:
    from aip_agent.context import Context

CLASSIFIER_SYSTEM_INSTRUCTION = """
You are a precise intent classifier that analyzes input requests to determine their intended action or purpose.
You are provided with a request and a list of intents to choose from.
You can choose one or more intents, or choose none if no intent is appropriate.
"""


class OpenAILLMIntentClassifier(LLMIntentClassifier):
    """
    An LLM router that uses an OpenAI model to make routing decisions.
    """

    def __init__(
        self,
        intents: List[Intent],
        classification_instruction: str | None = None,
        context: Optional["Context"] = None,
        **kwargs,
    ):
        openai_llm = OpenAIAugmentedLLM(
            instruction=CLASSIFIER_SYSTEM_INSTRUCTION, context=context
        )

        super().__init__(
            llm=openai_llm,
            intents=intents,
            classification_instruction=classification_instruction,
            context=context,
            **kwargs,
        )

    @classmethod
    async def create(
        cls,
        intents: List[Intent],
        classification_instruction: str | None = None,
        context: Optional["Context"] = None,
    ) -> "OpenAILLMIntentClassifier":
        """
        Factory method to create and initialize a classifier.
        Use this instead of constructor since we need async initialization.
        """
        instance = cls(
            intents=intents,
            classification_instruction=classification_instruction,
            context=context,
        )
        await instance.initialize()
        return instance
