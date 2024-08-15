import json
import re
from textwrap import dedent
from typing import Optional, List, Iterator, Dict, Any


from kr8.llm.base import LLM
from kr8.llm.message import Message
from kr8.tools.function import FunctionCall
from kr8.utils.log import logger
from kr8.utils.timer import Timer
from kr8.utils.tools import (
    get_function_call_for_tool_call,
    extract_tool_from_xml,
    remove_function_calls_from_string,
)

try:
    from anthropic import Anthropic as AnthropicClient
    from anthropic.types import Message as AnthropicMessage
except ImportError:
    logger.error("`anthropic` not installed")
    raise


class Claude(LLM):
    name: str = "claude"
    model: str = "claude-3-opus-20240229"
    # -*- Request parameters
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    request_params: Optional[Dict[str, Any]] = None
    # -*- Client parameters
    api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    # -*- Provide the client manually
    anthropic_client: Optional[AnthropicClient] = None

    @property
    def client(self) -> AnthropicClient:
        if self.anthropic_client:
            return self.anthropic_client

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        return AnthropicClient(**_client_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        _request_params: Dict[str, Any] = {}
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.stop_sequences:
            _request_params["stop_sequences"] = self.stop_sequences
        if self.tools is not None:
            if _request_params.get("stop_sequences") is None:
                _request_params["stop_sequences"] = ["</function_calls>"]
            elif "</function_calls>" not in _request_params["stop_sequences"]:
                _request_params["stop_sequences"].append("</function_calls>")
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.top_k:
            _request_params["top_k"] = self.top_k
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def clean_response(self, response: str, is_final: bool = False) -> str:
        # Remove XML-like tags
        response = re.sub(r'<[^>]+>', '', response)
        
        # Remove specific tags like <search_knowledge_base>
        response = re.sub(r'<search_knowledge_base>.*?</search_knowledge_base>', '', response)
        
        # Add Markdown formatting for headers (modified to avoid look-behind)
        response = re.sub(r'^(\w[^:\n]*):(?=\s|$)', r'### \1', response, flags=re.MULTILINE)
        response = re.sub(r'\n(\w.+):(?=\s|$)', r'\n### \1', response)
        
        # Add Markdown formatting for bullet points (modified to avoid look-behind)
        response = re.sub(r'(^|\n)\* ', r'\1- ', response)
        
        # Only add "Simples!" at the end of the complete response
        if is_final and not response.strip().endswith("Simples!"):
            response += "\n\nSimples!"
        
        return response.strip()

    def _prepare_messages(self, messages: List[Message]) -> List[dict]:
        prepared_messages = []
        last_role = None
        for message in messages:
            if message.role == "system":
                continue  # We'll handle system messages separately
            if message.role != last_role:
                prepared_messages.append({"role": message.role, "content": message.content or ""})
                last_role = message.role
        
        # Ensure the conversation starts with a user message
        if prepared_messages and prepared_messages[0]["role"] != "user":
            prepared_messages.insert(0, {"role": "user", "content": "Hello"})
        
        return prepared_messages

    def invoke(self, messages: List[Message]) -> AnthropicMessage:
        api_kwargs: Dict[str, Any] = self.api_kwargs
        api_messages = self._prepare_messages(messages)

        # Only use the most recent system message and user query
        system_message = next((m.content for m in reversed(messages) if m.role == "system"), None)
        user_message = next((m for m in reversed(messages) if m.role == "user"), None)

        if system_message:
            api_kwargs["system"] = system_message

        # Use only the most recent user message to start a fresh conversation
        api_messages = [{"role": "user", "content": user_message.content}] if user_message else []

        return self.client.messages.create(
            model=self.model,
            messages=api_messages,
            **api_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Any:
        api_kwargs: Dict[str, Any] = self.api_kwargs
        api_messages = self._prepare_messages(messages)

        # Only use the most recent system message and user query
        system_message = next((m.content for m in reversed(messages) if m.role == "system"), None)
        user_message = next((m for m in reversed(messages) if m.role == "user"), None)

        if system_message:
            api_kwargs["system"] = system_message

        # Use only the most recent user message to start a fresh conversation
        api_messages = [{"role": "user", "content": user_message.content}] if user_message else []

        return self.client.messages.stream(
            model=self.model,
            messages=api_messages,
            **api_kwargs,
        )
        
    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- Claude Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: AnthropicMessage = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Parse response
        response_content = response.content[0].text

        # -*- Create assistant message
        assistant_message = Message(
            role=response.role or "assistant",
            content=response_content,
        )

        # Check if the response contains a tool call
        try:
            if response_content is not None:
                if "<function_calls>" in response_content:
                    # List of tool calls added to the assistant message
                    tool_calls: List[Dict[str, Any]] = []

                    # Add function call closing tag to the assistant message
                    # This is because we add </function_calls> as a stop sequence
                    assistant_message.content += "</function_calls>"  # type: ignore

                    # If the assistant is calling multiple functions, the response will contain multiple <invoke> tags
                    response_content = response_content.split("</invoke>")
                    for tool_call_response in response_content:
                        if "<invoke>" in tool_call_response:
                            # Extract tool call string from response
                            tool_call_dict = extract_tool_from_xml(tool_call_response)
                            tool_call_name = tool_call_dict.get("tool_name")
                            tool_call_args = tool_call_dict.get("parameters")
                            function_def = {"name": tool_call_name}
                            if tool_call_args is not None:
                                function_def["arguments"] = json.dumps(tool_call_args)
                            tool_calls.append(
                                {
                                    "type": "function",
                                    "function": function_def,
                                }
                            )
                            logger.debug(f"Tool Calls: {tool_calls}")

                    if len(tool_calls) > 0:
                        assistant_message.tool_calls = tool_calls
        except Exception as e:
            logger.warning(e)
            pass

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
            # Remove the tool call from the response content
            final_response = remove_function_calls_from_string(assistant_message.content)  # type: ignore
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
            if len(function_call_results) > 0:
                fc_responses = "<function_results>"

                for _fc_message in function_call_results:
                    fc_responses += "<result>"
                    fc_responses += "<tool_name>" + _fc_message.tool_call_name + "</tool_name>"  # type: ignore
                    fc_responses += "<stdout>" + _fc_message.content + "</stdout>"  # type: ignore
                    fc_responses += "</result>"
                fc_responses += "</function_results>"

                messages.append(Message(role="user", content=fc_responses))

            # -*- Yield new response using results of tool calls
            final_response += self.response(messages=messages)
            return final_response
        logger.debug("---------- Claude Response End ----------")
        # -*- Return content if no function calls are present
        if assistant_message.content is not None:            
            return self.clean_response(assistant_message.get_content_string())            
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Claude Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_content = ""
        tool_calls_counter = 0
        response_is_tool_call = False
        is_closing_tool_call_tag = False
        response_timer = Timer()
        response_timer.start()
        response = self.invoke_stream(messages=messages)
        
        buffer = ""
        with response as stream:
            for stream_delta in stream.text_stream:
                if stream_delta is not None:
                    buffer += stream_delta
                    assistant_message_content += stream_delta

                    # Detect if response is a tool call
                    if not response_is_tool_call and ("<function" in buffer or "<invoke" in buffer):
                        response_is_tool_call = True

                    # If response is a tool call, count the number of tool calls
                    if response_is_tool_call:
                        if "<invoke" in buffer:
                            tool_calls_counter += 1
                        if buffer.strip().endswith("</invoke>"):
                            tool_calls_counter -= 1
                        if tool_calls_counter == 0 and buffer.strip().endswith(">"):
                            response_is_tool_call = False
                            is_closing_tool_call_tag = True

                    # Yield content if not a tool call
                    if not response_is_tool_call:
                        if is_closing_tool_call_tag and buffer.strip().endswith(">"):
                            is_closing_tool_call_tag = False
                            buffer = ""
                            continue

                        # Clean and yield the buffer when it reaches a certain size or contains a full sentence
                        if len(buffer) > 50 or re.search(r'[.!?\n](?=\s|$)', buffer):
                            cleaned_buffer = self.clean_response(buffer, is_final=False)
                            if cleaned_buffer:
                                yield cleaned_buffer + " "  # Add a space for smoother rendering
                            buffer = ""

        # Yield any remaining content in the buffer
        if buffer:
            cleaned_buffer = self.clean_response(buffer, is_final=True)
            if cleaned_buffer:
                yield cleaned_buffer

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        
        # Add function call closing tag to the assistant message
        if assistant_message_content.count("<function_calls>") == 1:
            assistant_message_content += "</function_calls>"

        # -*- Create assistant message
        assistant_message = Message(
            role="assistant",
            content=assistant_message_content,
        )

        # Check if the response contains tool calls
        try:
            if "<invoke>" in assistant_message_content and "</invoke>" in assistant_message_content:
                # List of tool calls added to the assistant message
                tool_calls: List[Dict[str, Any]] = []
                # Break the response into tool calls
                tool_call_responses = assistant_message_content.split("</invoke>")
                for tool_call_response in tool_call_responses:
                    # Add back the closing tag if this is not the last tool call
                    if tool_call_response != tool_call_responses[-1]:
                        tool_call_response += "</invoke>"

                    if "<invoke>" in tool_call_response and "</invoke>" in tool_call_response:
                        # Extract tool call string from response
                        tool_call_dict = extract_tool_from_xml(tool_call_response)
                        tool_call_name = tool_call_dict.get("tool_name")
                        tool_call_args = tool_call_dict.get("parameters")
                        function_def = {"name": tool_call_name}
                        if tool_call_args is not None:
                            function_def["arguments"] = json.dumps(tool_call_args)
                        tool_calls.append(
                            {
                                "type": "function",
                                "function": function_def,
                            }
                        )
                        logger.debug(f"Tool Calls: {tool_calls}")

                # If tool call parsing is successful, add tool calls to the assistant message
                if len(tool_calls) > 0:
                    assistant_message.tool_calls = tool_calls
        except Exception:
            logger.warning(f"Could not parse tool calls from response: {assistant_message_content}")
            pass

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
                    yield self.clean_response(f"- Running: {function_calls_to_run[0].get_call_str()}\n\n")
                elif len(function_calls_to_run) > 1:
                    yield self.clean_response("Running:")
                    for _f in function_calls_to_run:
                        yield self.clean_response(f"\n - {_f.get_call_str()}")
                    yield self.clean_response("\n\n")

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")
            # Add results of the function calls to the messages
            if len(function_call_results) > 0:
                fc_responses = "<function_results>"

                for _fc_message in function_call_results:
                    fc_responses += "<result>"
                    fc_responses += "<tool_name>" + _fc_message.tool_call_name + "</tool_name>"  # type: ignore
                    fc_responses += "<stdout>" + _fc_message.content + "</stdout>"  # type: ignore
                    fc_responses += "</result>"
                fc_responses += "</function_results>"

                messages.append(Message(role="user", content=fc_responses))

            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)
        logger.debug("---------- Claude Response End ----------")

    def get_tool_call_prompt(self) -> Optional[str]:
        if self.functions is not None and len(self.functions) > 0:
            tool_call_prompt = dedent(
                """\
            In this environment you have access to a set of tools you can use to answer the user's question.

            You may call them like this:
            <function_calls>
            <invoke>
            <tool_name>$TOOL_NAME</tool_name>
            <parameters>
            <$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>
            ...
            </parameters>
            </invoke>
            </function_calls>
            """
            )
            tool_call_prompt += "\nHere are the tools available:"
            tool_call_prompt += "\n<tools>"
            for _f_name, _function in self.functions.items():
                _function_def = _function.get_definition_for_prompt_dict()
                if _function_def:
                    tool_call_prompt += "\n<tool_description>"
                    tool_call_prompt += f"\n<tool_name>{_function_def.get('name')}</tool_name>"
                    tool_call_prompt += f"\n<description>{_function_def.get('description')}</description>"
                    arguments = _function_def.get("arguments")
                    if arguments:
                        tool_call_prompt += "\n<parameters>"
                        for arg in arguments:
                            tool_call_prompt += "\n<parameter>"
                            tool_call_prompt += f"\n<name>{arg}</name>"
                            if isinstance(arguments.get(arg).get("type"), str):
                                tool_call_prompt += f"\n<type>{arguments.get(arg).get('type')}</type>"
                            else:
                                tool_call_prompt += f"\n<type>{arguments.get(arg).get('type')[0]}</type>"
                            tool_call_prompt += "\n</parameter>"
                    tool_call_prompt += "\n</parameters>"
                    tool_call_prompt += "\n</tool_description>"
            tool_call_prompt += "\n</tools>"
            return tool_call_prompt
        return None

    def get_system_prompt_from_llm(self) -> Optional[str]:
        return self.get_tool_call_prompt()
