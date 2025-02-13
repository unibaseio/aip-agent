import asyncio

from mcp_agent.human_input.types import (
    HumanInputRequest,
    HumanInputResponse,
)


async def console_input_callback(request: HumanInputRequest) -> HumanInputResponse:
    """Request input from a human user via console."""

    if request.description:
        print(f"\n[HUMAN INPUT NEEDED] {request.description}")
    print(f"\n{request.prompt}")

    if request.timeout_seconds:
        try:
            # Use run_in_executor to make input non-blocking
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, input, "Enter response: "),
                request.timeout_seconds,
            )
        except asyncio.TimeoutError:
            print("\nTimeout waiting for input")
            raise TimeoutError("No response received within timeout period")
    else:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, input, "Enter response: ")

    return HumanInputResponse(request_id=request.request_id, response=response.strip())
