import json
from textwrap import dedent
from typing import Optional, List, Dict, Any, Iterator

from src.backend.kr8.llm.base import LLM
from src.backend.kr8.llm.message import Message
from src.backend.kr8.tools.function import FunctionCall
from src.backend.kr8.utils.log import logger
from src.backend.kr8.utils.timer import Timer
from src.backend.kr8.utils.tools import get_function_call_for_tool_call

try:
    from cohere import Client as CohereClient
    from cohere.types.tool import Tool as CohereTool
    from cohere.types.tool_call import ToolCall as CohereToolCall
    from cohere.types.non_streamed_chat_response import NonStreamedChatResponse
    from cohere.types.streamed_chat_response import (
        StreamedChatResponse,
        StreamedChatResponse_StreamStart,
        StreamedChatResponse_TextGeneration,
        StreamedChatResponse_ToolCallsGeneration,
    )
    from cohere.types.chat_request_tool_results_item import ChatRequestToolResultsItem
    from cohere.types.tool_parameter_definitions_value import ToolParameterDefinitionsValue
except ImportError:
    logger.error("`cohere` not installed")
    raise


class CohereChat(LLM):
    name: str = "cohere"
    model: str = "command-r"
    # -*- Request parameters
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    request_params: Optional[Dict[str, Any]] = None
    # Add chat history to the cohere messages instead of using the conversation_id
    add_chat_history: bool = False
    # -*- Client parameters
    api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    # -*- Provide the Cohere client manually
    cohere_client: Optional[CohereClient] = None

    @property
    def client(self) -> CohereClient:
        if self.cohere_client:
            return self.cohere_client

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        return CohereClient(**_client_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        _request_params: Dict[str, Any] = {}
        if self.run_id is not None:
            _request_params["conversation_id"] = self.run_id
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.top_k:
            _request_params["top_k"] = self.top_k
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.frequency_penalty:
            _request_params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty:
            _request_params["presence_penalty"] = self.presence_penalty
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def get_tools(self) -> Optional[List[CohereTool]]:
        if not self.functions:
            return None

        # Returns the tools in the format required by the Cohere API
        return [
            CohereTool(
                name=f_name,
                description=function.description or "",
                parameter_definitions={
                    param_name: ToolParameterDefinitionsValue(
                        type=param_info["type"] if isinstance(param_info["type"], str) else param_info["type"][0],
                        required="null" not in param_info["type"],
                    )
                    for param_name, param_info in function.parameters.get("properties", {}).items()
                },
            )
            for f_name, function in self.functions.items()
        ]

    def invoke(
        self, messages: List[Message], tool_results: Optional[List[ChatRequestToolResultsItem]] = None
    ) -> NonStreamedChatResponse:
        api_kwargs: Dict[str, Any] = self.api_kwargs
        chat_message: Optional[str] = None

        if self.add_chat_history:
            logger.debug("Providing chat_history to cohere")
            chat_history = []
            for m in messages:
                if m.role == "system" and "preamble" not in api_kwargs:
                    api_kwargs["preamble"] = m.content
                elif m.role == "user":
                    if chat_message is not None:
                        # Add the existing chat_message to the chat_history
                        chat_history.append({"role": "USER", "message": chat_message})
                    # Update the chat_message to the new user message
                    chat_message = m.get_content_string()
                else:
                    chat_history.append({"role": "CHATBOT", "message": m.get_content_string() or ""})
            api_kwargs["chat_history"] = chat_history
        else:
            # Set first system message as preamble
            for m in messages:
                if m.role == "system" and "preamble" not in api_kwargs:
                    api_kwargs["preamble"] = m.get_content_string()
                    break
            # Set last user message as chat_message
            for m in reversed(messages):
                if m.role == "user":
                    chat_message = m.get_content_string()
                    break

        if self.tools:
            api_kwargs["tools"] = self.get_tools()

        if tool_results:
            api_kwargs["tool_results"] = tool_results

        return self.client.chat(message=chat_message or "", model=self.model, **api_kwargs)

    def invoke_stream(
        self, messages: List[Message], tool_results: Optional[List[ChatRequestToolResultsItem]] = None
    ) -> Iterator[StreamedChatResponse]:
        api_kwargs: Dict[str, Any] = self.api_kwargs
        chat_message: Optional[str] = None

        if self.add_chat_history:
            logger.debug("Providing chat_history to cohere")
            chat_history = []
            for m in messages:
                if m.role == "system" and "preamble" not in api_kwargs:
                    api_kwargs["preamble"] = m.get_content_string()
                elif m.role == "user":
                    if chat_message is not None:
                        # Add the existing chat_message to the chat_history
                        chat_history.append({"role": "USER", "message": chat_message})
                    # Update the chat_message to the new user message
                    chat_message = m.get_content_string()
                else:
                    chat_history.append({"role": "CHATBOT", "message": m.get_content_string() or ""})
            api_kwargs["chat_history"] = chat_history
        else:
            # Set first system message as preamble
            for m in messages:
                if m.role == "system" and "preamble" not in api_kwargs:
                    api_kwargs["preamble"] = m.get_content_string()
                    break
            # Set last user message as chat_message
            for m in reversed(messages):
                if m.role == "user":
                    chat_message = m.get_content_string()
                    break

        if self.tools:
            api_kwargs["tools"] = self.get_tools()

        if tool_results:
            api_kwargs["tool_results"] = tool_results

        logger.debug(f"Chat message: {chat_message}")
        return self.client.chat_stream(message=chat_message or "", model=self.model, **api_kwargs)

    def response(self, messages: List[Message], tool_results: Optional[List[ChatRequestToolResultsItem]] = None) -> str:
        logger.debug("---------- Cohere Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: NonStreamedChatResponse = self.invoke(messages=messages, tool_results=tool_results)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Parse response
        response_content = response.text
        response_tool_calls: Optional[List[CohereToolCall]] = response.tool_calls

        # -*- Create assistant message
        assistant_message = Message(role="assistant", content=response_content)

        # -*- Get tool calls from response
        if response_tool_calls:
            tool_calls: List[Dict[str, Any]] = []
            for tools in response_tool_calls:
                tool_calls.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tools.name,
                            "arguments": json.dumps(tools.parameters),
                        },
                    }
                )
            if len(tool_calls) > 0:
                assistant_message.tool_calls = tool_calls

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Run function call
        if assistant_message.tool_calls is not None and self.run_tools:
            final_response = ""
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="user", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="user", content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    final_response += f" - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    final_response += "Running:"
                    for _f in function_calls_to_run:
                        final_response += f"\n - {_f.get_call_str()}"
                    final_response += "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")

            # Making sure the length of tool calls and function call results are the same to avoid unexpected behavior
            if response_tool_calls is not None and 0 < len(function_call_results) == len(response_tool_calls):
                # Constructs a list named tool_results, where each element is a dictionary that contains details of tool calls and their outputs.
                # It pairs each tool call in response_tool_calls with its corresponding result in function_call_results.
                tool_results = [
                    ChatRequestToolResultsItem(
                        call=tool_call, outputs=[tool_call.parameters, {"result": fn_result.content}]
                    )
                    for tool_call, fn_result in zip(response_tool_calls, function_call_results)
                ]
                messages.append(Message(role="user", content="Tool result"))
                # logger.debug(f"Tool results: {tool_results}")

            # -*- Yield new response using results of tool calls
            final_response += self.response(messages=messages, tool_results=tool_results)
            return final_response
        logger.debug("---------- Cohere Response End ----------")
        # -*- Return content if no function calls are present
        if assistant_message.content is not None:
            return assistant_message.get_content_string()
        return "Something went wrong, please try again."

    def response_stream(
        self, messages: List[Message], tool_results: Optional[List[ChatRequestToolResultsItem]] = None
    ) -> Any:
        logger.debug("---------- Cohere Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_content = ""
        tool_calls: List[Dict[str, Any]] = []
        response_tool_calls: List[CohereToolCall] = []
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_stream(messages=messages, tool_results=tool_results):
            # logger.debug(f"Cohere response type: {type(response)}")
            # logger.debug(f"Cohere response: {response}")

            if isinstance(response, StreamedChatResponse_StreamStart):
                pass

            if isinstance(response, StreamedChatResponse_TextGeneration):
                if response.text is not None:
                    assistant_message_content += response.text

                    yield response.text

            # Detect if response is a tool call
            if isinstance(response, StreamedChatResponse_ToolCallsGeneration):
                for tc in response.tool_calls:
                    response_tool_calls.append(tc)
                    tool_calls.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.parameters),
                            },
                        }
                    )

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(role="assistant", content=assistant_message_content)
        # -*- Add tool calls to assistant message
        if len(tool_calls) > 0:
            assistant_message.tool_calls = tool_calls

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function call
        if assistant_message.tool_calls is not None and self.run_tools:
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="user", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="user", content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    yield f"- Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "Running:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")

            # Making sure the length of tool calls and function call results are the same to avoid unexpected behavior
            if response_tool_calls is not None and 0 < len(function_call_results) == len(tool_calls):
                # Constructs a list named tool_results, where each element is a dictionary that contains details of tool calls and their outputs.
                # It pairs each tool call in response_tool_calls with its corresponding result in function_call_results.
                tool_results = [
                    ChatRequestToolResultsItem(
                        call=tool_call, outputs=[tool_call.parameters, {"result": fn_result.content}]
                    )
                    for tool_call, fn_result in zip(response_tool_calls, function_call_results)
                ]
                messages.append(Message(role="user", content="Tool result"))
                # logger.debug(f"Tool results: {tool_results}")

            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages, tool_results=tool_results)
        logger.debug("---------- Cohere Response End ----------")

    def get_tool_call_prompt(self) -> Optional[str]:
        if self.functions is not None and len(self.functions) > 0:
            preamble = """\
            ## Task & Context
            You help people answer their questions and other requests interactively. You will be asked a very wide array of requests on all kinds of topics. You will be equipped with a wide range of search engines or similar tools to help you, which you use to research your answer. You should focus on serving the user's needs as best you can, which will be wide-ranging.


            ## Style Guide
            Unless the user asks for a different style of answer, you should answer in full sentences, using proper grammar and spelling.

            """
            return dedent(preamble)

        return None

    def get_system_prompt_from_llm(self) -> Optional[str]:
        return self.get_tool_call_prompt()
