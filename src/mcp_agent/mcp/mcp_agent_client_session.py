"""
A derived client session for the MCP Agent framework.
It adds logging and supports sampling requests.
"""

from mcp import ClientSession
from mcp.shared.session import (
    RequestResponder,
    ReceiveResultT,
    ReceiveNotificationT,
    RequestId,
    SendNotificationT,
    SendRequestT,
    SendResultT,
)
from mcp.types import (
    ClientResult,
    CreateMessageRequest,
    CreateMessageResult,
    ErrorData,
    JSONRPCNotification,
    JSONRPCRequest,
    ServerRequest,
    TextContent,
)

from mcp_agent.context_dependent import ContextDependent
from mcp_agent.logging.logger import get_logger

logger = get_logger(__name__)


class MCPAgentClientSession(ClientSession, ContextDependent):
    """
    MCP Agent framework acts as a client to the servers providing tools/resources/prompts for the agent workloads.
    This is a simple client session for those server connections, and supports
        - handling sampling requests
        - notifications

    Developers can extend this class to add more custom functionality as needed
    """

    async def initialize(self) -> None:
        logger.debug("initialize...")
        try:
            await super().initialize()
            logger.debug("initialized")
        except Exception as e:
            logger.error(f"initialize failed: {e}")
            raise

    async def __aenter__(self):
        # logger.debug(
        #     f"__aenter__ {str(self)}: current_task={anyio.get_current_task()}, id={id(anyio.get_current_task())}"
        # )
        return await super().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # logger.debug(
        #     f"__aexit__ {str(self)}: current_task={anyio.get_current_task()}, id={id(anyio.get_current_task())}"
        # )
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    async def _received_request(
        self, responder: RequestResponder[ServerRequest, ClientResult]
    ) -> None:
        logger.debug("Received request:", data=responder.request.model_dump())
        request = responder.request.root

        if isinstance(request, CreateMessageRequest):
            return await self.handle_sampling_request(request, responder)

        # Handle other requests as usual
        await super()._received_request(responder)

    async def send_request(
        self,
        request: SendRequestT,
        result_type: type[ReceiveResultT],
    ) -> ReceiveResultT:
        logger.debug("send_request: request=", data=request.model_dump())
        try:
            result = await super().send_request(request, result_type)
            logger.debug("send_request: response=", data=result.model_dump())
            return result
        except Exception as e:
            logger.error(f"send_request failed: {e}")
            raise

    async def send_notification(self, notification: SendNotificationT) -> None:
        logger.debug("send_notification:", data=notification.model_dump())
        try:
            return await super().send_notification(notification)
        except Exception as e:
            logger.error("send_notification failed", data=e)
            raise

    async def _send_response(
        self, request_id: RequestId, response: SendResultT | ErrorData
    ) -> None:
        logger.debug(
            f"send_response: request_id={request_id}, response=",
            data=response.model_dump(),
        )
        return await super()._send_response(request_id, response)

    async def _received_notification(self, notification: ReceiveNotificationT) -> None:
        """
        Can be overridden by subclasses to handle a notification without needing
        to listen on the message stream.
        """
        logger.info(
            "_received_notification: notification=",
            data=notification.model_dump(),
        )
        return await super()._received_notification(notification)

    async def send_progress_notification(
        self, progress_token: str | int, progress: float, total: float | None = None
    ) -> None:
        """
        Sends a progress notification for a request that is currently being
        processed.
        """
        logger.debug(
            "send_progress_notification: progress_token={progress_token}, progress={progress}, total={total}"
        )
        return await super().send_progress_notification(
            progress_token=progress_token, progress=progress, total=total
        )

    async def _receive_loop(self) -> None:
        async with (
            self._read_stream,
            self._write_stream,
            self._incoming_message_stream_writer,
        ):
            async for message in self._read_stream:
                if isinstance(message, Exception):
                    await self._incoming_message_stream_writer.send(message)
                elif isinstance(message.root, JSONRPCRequest):
                    validated_request = self._receive_request_type.model_validate(
                        message.root.model_dump(
                            by_alias=True, mode="json", exclude_none=True
                        )
                    )
                    responder = RequestResponder(
                        request_id=message.root.id,
                        request_meta=validated_request.root.params.meta
                        if validated_request.root.params
                        else None,
                        request=validated_request,
                        session=self,
                    )

                    await self._received_request(responder)
                    if not responder._responded:
                        await self._incoming_message_stream_writer.send(responder)
                elif isinstance(message.root, JSONRPCNotification):
                    notification = self._receive_notification_type.model_validate(
                        message.root.model_dump(
                            by_alias=True, mode="json", exclude_none=True
                        )
                    )

                    await self._received_notification(notification)
                    await self._incoming_message_stream_writer.send(notification)
                else:  # Response or error
                    stream = self._response_streams.pop(message.root.id, None)
                    if stream:
                        await stream.send(message.root)
                    else:
                        await self._incoming_message_stream_writer.send(
                            RuntimeError(
                                "Received response with an unknown "
                                f"request ID: {message}"
                            )
                        )

    async def handle_sampling_request(
        self,
        request: CreateMessageRequest,
        responder: RequestResponder[ServerRequest, ClientResult],
    ):
        logger.info("Handling sampling request: %s", request)
        config = self.context.config
        session = self.context.upstream_session
        if session is None:
            # TODO: saqadri - consider whether we should be handling the sampling request here as a client
            logger.warning(
                "Error: No upstream client available for sampling requests. Request:",
                data=request,
            )
            try:
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=config.anthropic.api_key)

                params = request.params
                response = await client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=params.maxTokens,
                    messages=[
                        {
                            "role": m.role,
                            "content": m.content.text
                            if hasattr(m.content, "text")
                            else m.content.data,
                        }
                        for m in params.messages
                    ],
                    system=getattr(params, "systemPrompt", None),
                    temperature=getattr(params, "temperature", 0.7),
                    stop_sequences=getattr(params, "stopSequences", None),
                )

                await responder.respond(
                    CreateMessageResult(
                        model="claude-3-sonnet-20240229",
                        role="assistant",
                        content=TextContent(type="text", text=response.content[0].text),
                    )
                )
            except Exception as e:
                logger.error(f"Error handling sampling request: {e}")
                await responder.respond(ErrorData(code=-32603, message=str(e)))
        else:
            try:
                # If a session is available, we'll pass-through the sampling request to the upstream client
                result = await session.send_request(
                    request=ServerRequest(request), result_type=CreateMessageResult
                )

                # Pass the result from the upstream client back to the server. We just act as a pass-through client here.
                await responder.send_result(result)
            except Exception as e:
                await responder.send_error(code=-32603, message=str(e))
