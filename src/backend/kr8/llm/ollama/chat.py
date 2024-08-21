import json
import httpx
from textwrap import dedent
from typing import Optional, List, Iterator, Dict, Any, Mapping, Union
from src.backend.kr8.llm.base import LLM
from src.backend.kr8.llm.message import Message
from src.backend.kr8.tools.function import FunctionCall
from src.backend.kr8.utils.log import logger
from src.backend.kr8.utils.timer import Timer
from src.backend.kr8.utils.tools import get_function_call_for_tool_call
from src.backend.kr8.llm.offline_llm import OfflineLLM
from tenacity import retry, stop_after_attempt, wait_fixed

try:
    from ollama import Client as OllamaClient
except ImportError:
    logger.error("`ollama` not installed")
    raise

class Ollama(LLM):
    name: str = "Ollama"
    model: str
    base_url: str
    host: Optional[str] = None
    timeout: Optional[Any] = None
    format: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    keep_alive: Optional[Union[float, str]] = None
    client_kwargs: Optional[Dict[str, Any]] = None
    ollama_client: Optional[OllamaClient] = None
    function_call_limit: int = 5
    deactivate_tools_after_use: bool = False
    add_user_message_after_tool_call: bool = True
    max_context_tokens: int = 2048  # Adjust based on the specific Ollama model

    @property
    def client(self) -> OllamaClient:
        if self.ollama_client is None:
            _ollama_params: Dict[str, Any] = {"host": self.base_url}
            if self.timeout:
                _ollama_params["timeout"] = self.timeout
            if self.client_kwargs:
                _ollama_params.update(self.client_kwargs)
            self.ollama_client = OllamaClient(**_ollama_params)
        return self.ollama_client

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.format is not None:
            kwargs["format"] = self.format
        elif self.response_format is not None:
            if self.response_format.get("type") == "json_object":
                kwargs["format"] = "json"
        if self.options is not None:
            kwargs["options"] = self.options
        if self.keep_alive is not None:
            kwargs["keep_alive"] = self.keep_alive
        return kwargs

    def to_dict(self) -> Dict[str, Any]:
        _dict = super().to_dict()
        if self.host:
            _dict["host"] = self.host
        if self.timeout:
            _dict["timeout"] = self.timeout
        if self.format:
            _dict["format"] = self.format
        if self.response_format:
            _dict["response_format"] = self.response_format
        return _dict

    def to_llm_message(self, message: Message) -> Dict[str, Any]:
        msg = {
            "role": message.role,
            "content": message.content,
        }
        if message.model_extra is not None and "images" in message.model_extra:
            msg["images"] = message.model_extra.get("images")
        return msg

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def invoke_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:
        try:
            logger.debug(f"Attempting to connect to Ollama service at: {self.base_url}")
            yield from self.client.chat(
                model=self.model,
                messages=[self.to_llm_message(m) for m in messages],
                stream=True,
                **self.api_kwargs,
            )
        except httpx.ConnectError as e:
            logger.warning(f"invoke_stream - Failed to connect to Ollama service: {e}")
            logger.warning(f"Connection details: Base URL: {self.base_url}, Model: {self.model}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in invoke_stream: {e}")
            raise

    def offline_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:
        offline_llm = OfflineLLM(model=self.model)
        yield from offline_llm.invoke_stream(messages)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def invoke(self, messages: List[Message]) -> Mapping[str, Any]:
        try:
            logger.debug(f"Attempting to connect to Ollama service at: {self.base_url}")
            logger.debug(f"Invoking Ollama model with messages: {messages}")
            response = self.client.chat(
                model=self.model,
                messages=[self.to_llm_message(m) for m in messages],
                **self.api_kwargs,
            )
            logger.debug(f"Ollama model response: {response}")
            return response
        except httpx.ConnectError as e:
            logger.warning(f"invoke - Failed to connect to Ollama service: {e}")
            logger.warning(f"Connection details: Base URL: {self.base_url}, Model: {self.model}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in invoke: {e}")
            raise

    def deactivate_function_calls(self) -> None:
        self.format = ""

    def inject_context(self, messages: List[Message], context: str) -> List[Message]:
        context_message = Message(
            role="system",
            content=f"Use the following context to answer the user's question:\n\n{context}\n\nNow, answer the user's question based on this context."
        )
        return [context_message] + messages

    def truncate_context(self, context: str, max_tokens: int) -> str:
        # Simple truncation, you might want to implement a more sophisticated method
        words = context.split()
        if len(words) > max_tokens:
            return ' '.join(words[:max_tokens]) + "..."
        return context

    def validate_response_uses_context(self, response: str, context: str) -> bool:
        # Implement a simple check for key phrases from the context
        # You might want to use more sophisticated methods like semantic similarity
        key_phrases = context.split('.')[:3]  # Use first 3 sentences as key phrases
        return any(phrase.strip().lower() in response.lower() for phrase in key_phrases if phrase.strip())

    def requery_with_context_emphasis(self, messages: List[Message], context: str) -> str:
        emphasis_message = Message(
            role="user",
            content="Your previous response didn't use the provided context. Please answer the question using ONLY the information provided in the context."
        )
        messages.append(emphasis_message)
        return self.response(self.inject_context(messages, context))

    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- Ollama Response Start ----------")
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        try:
            response: Mapping[str, Any] = self.invoke(messages=messages)
        except Exception:
            logger.warning("All attempts to connect failed. Switching to offline mode.")
            offline_llm = OfflineLLM(model=self.model)
            return offline_llm.response(messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        response_message: Mapping[str, Any] = response.get("message", {})
        response_role = response_message.get("role")
        response_content: Optional[str] = response_message.get("content")

        assistant_message = Message(
            role=response_role or "assistant",
            content=response_content,
        )

        # Check for tool calls in the response
        try:
            if response_content is not None:
                _tool_call_content = response_content.strip()
                if _tool_call_content.startswith("{") and _tool_call_content.endswith("}"):
                    _tool_call_content_json = json.loads(_tool_call_content)
                    if "tool_calls" in _tool_call_content_json:
                        assistant_tool_calls = _tool_call_content_json.get("tool_calls")
                        if isinstance(assistant_tool_calls, list):
                            tool_calls: List[Dict[str, Any]] = []
                            logger.debug(f"Building tool calls from {assistant_tool_calls}")
                            for tool_call in assistant_tool_calls:
                                tool_call_name = tool_call.get("name")
                                tool_call_args = tool_call.get("arguments")
                                _function_def = {"name": tool_call_name}
                                if tool_call_args is not None:
                                    _function_def["arguments"] = json.dumps(tool_call_args)
                                tool_calls.append(
                                    {
                                        "type": "function",
                                        "function": _function_def,
                                    }
                                )
                            assistant_message.tool_calls = tool_calls
                            assistant_message.role = "assistant"
        except Exception:
            logger.warning(f"Could not parse tool calls from response: {response_content}")
            pass

        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        messages.append(assistant_message)
        assistant_message.log()

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
                    final_response += f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    final_response += "\nRunning:"
                    for _f in function_calls_to_run:
                        final_response += f"\n - {_f.get_call_str()}"
                    final_response += "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
                if self.add_user_message_after_tool_call:
                    messages = self.add_original_user_message(messages)

            if self.deactivate_tools_after_use:
                self.deactivate_function_calls()

            final_response += self.response(messages=messages)
            return final_response
        logger.debug("---------- Ollama Response End ----------")
        if assistant_message.content is not None:
            return assistant_message.get_content_string()
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Ollama Response Start ----------")
        for m in messages:
            m.log()

        assistant_message_content = ""
        response_is_tool_call = False
        tool_call_bracket_count = 0
        is_last_tool_call_bracket = False
        completion_tokens = 0
        time_to_first_token = None
        response_timer = Timer()
        response_timer.start()
        try:
            for response in self.invoke_stream(messages=messages):
                completion_tokens += 1
                if completion_tokens == 1:
                    time_to_first_token = response_timer.elapsed
                    logger.debug(f"Time to first token: {time_to_first_token:.4f}s")

                response_message: Optional[dict] = response.get("message")
                response_content = response_message.get("content") if response_message else None

                if response_content is not None:
                    assistant_message_content += response_content

                if not response_is_tool_call and assistant_message_content.strip().startswith("{"):
                    response_is_tool_call = True

                if response_is_tool_call and response_content is not None:
                    if "{" in response_content.strip():
                        tool_call_bracket_count += response_content.strip().count("{")
                    if "}" in response_content.strip():
                        tool_call_bracket_count -= response_content.strip().count("}")
                        if tool_call_bracket_count == 0:
                            response_is_tool_call = False
                            is_last_tool_call_bracket = True

                if not response_is_tool_call and response_content is not None:
                    if is_last_tool_call_bracket and response_content.strip().endswith("}"):
                        is_last_tool_call_bracket = False
                        continue

                    yield response_content
        except httpx.ConnectError:
            logger.warning("Failed to connect to Ollama service. Switching to offline mode.")
            offline_llm = OfflineLLM()
            yield from offline_llm.response_stream(messages)
            return

        response_timer.stop()
        logger.debug(f"Tokens generated: {completion_tokens}")
        if completion_tokens > 0:
            logger.debug(f"Time per output token: {response_timer.elapsed / completion_tokens:.4f}s")
            logger.debug(f"Throughput: {completion_tokens / response_timer.elapsed:.4f} tokens/s")
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        assistant_message = Message(
            role="assistant",
            content=assistant_message_content,
        )
        try:
            if response_is_tool_call and assistant_message_content != "":
                _tool_call_content = assistant_message_content.strip()
                if _tool_call_content.startswith("{") and _tool_call_content.endswith("}"):
                    _tool_call_content_json = json.loads(_tool_call_content)
                    if "tool_calls" in _tool_call_content_json:
                        assistant_tool_calls = _tool_call_content_json.get("tool_calls")
                        if isinstance(assistant_tool_calls, list):
                            tool_calls: List[Dict[str, Any]] = []
                            logger.debug(f"Building tool calls from {assistant_tool_calls}")
                            for tool_call in assistant_tool_calls:
                                tool_call_name = tool_call.get("name")
                                tool_call_args = tool_call.get("arguments")
                                _function_def = {"name": tool_call_name}
                                if tool_call_args is not None:
                                    _function_def["arguments"] = json.dumps(tool_call_args)
                                tool_calls.append(
                                    {
                                        "type": "function",
                                        "function": _function_def,
                                    }
                                )
                            assistant_message.tool_calls = tool_calls
        except Exception:
            logger.warning(f"Could not parse tool calls from response: {assistant_message_content}")
            pass

        assistant_message.metrics["time"] = f"{response_timer.elapsed:.4f}"
        if time_to_first_token is not None:
            assistant_message.metrics["time_to_first_token"] = f"{time_to_first_token:.4f}s"
        if completion_tokens > 0:
            assistant_message.metrics["time_per_output_token"] = f"{response_timer.elapsed / completion_tokens:.4f}s"
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)
        if time_to_first_token is not None:
            if "time_to_first_token" not in self.metrics:
                self.metrics["time_to_first_token"] = []
            self.metrics["time_to_first_token"].append(f"{time_to_first_token:.4f}s")
        if completion_tokens > 0:
            if "tokens_per_second" not in self.metrics:
                self.metrics["tokens_per_second"] = []
            self.metrics["tokens_per_second"].append(f"{completion_tokens / response_timer.elapsed:.4f}")

        messages.append(assistant_message)
        assistant_message.log()

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
                    yield f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "\nRunning:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
                if self.add_user_message_after_tool_call:
                    messages = self.add_original_user_message(messages)

            if self.deactivate_tools_after_use:
                self.deactivate_function_calls()

            yield from self.response_stream(messages=messages)
        logger.debug("---------- Ollama Response End ----------")

    def add_original_user_message(self, messages: List[Message]) -> List[Message]:
        original_user_message_content = None
        for m in messages:
            if m.role == "user":
                original_user_message_content = m.content
                break
        if original_user_message_content is not None:
            _content = (
                "Using the results of the tools above, respond to the following message:"
                f"\n\n<user_message>\n{original_user_message_content}\n</user_message>"
            )
            messages.append(Message(role="user", content=_content))

        return messages

    def get_instructions_to_generate_tool_calls(self) -> List[str]:
        if self.functions is not None:
            return [
                "To respond to the user's message, you can use one or more of the tools provided above.",
                "If you decide to use a tool, you must respond in the JSON format matching the following schema:\n"
                + dedent(
                    """\
                    {
                        "tool_calls": [{
                            "name": "<name of the selected tool>",
                            "arguments": <parameters for the selected tool, matching the tool's JSON schema
                        }]
                    }\
                    """
                ),
                "To use a tool, just respond with the JSON matching the schema. Nothing else. Do not add any additional notes or explanations",
                "After you use a tool, the next message you get will contain the result of the tool call.",
                "REMEMBER: To use a tool, you must respond only in JSON format.",
                "After you use a tool and receive the result back, respond regularly to answer the user's question.",
            ]
        return []

    def get_tool_calls_definition(self) -> Optional[str]:
        if self.functions is not None:
            _tool_choice_prompt = "To respond to the user's message, you have access to the following tools:"
            for _f_name, _function in self.functions.items():
                _function_definition = _function.get_definition_for_prompt()
                if _function_definition:
                    _tool_choice_prompt += f"\n{_function_definition}"
            _tool_choice_prompt += "\n\n"
            return _tool_choice_prompt
        return None

    def get_system_prompt_from_llm(self) -> Optional[str]:
        base_prompt = self.get_tool_calls_definition()
        context_instruction = "\nAlways use the provided context to answer questions. If the context doesn't contain relevant information, say so."
        return base_prompt + context_instruction if base_prompt else context_instruction

    def get_instructions_from_llm(self) -> Optional[List[str]]:
        return self.get_instructions_to_generate_tool_calls()

    def process_with_context(self, messages: List[Message], context: str) -> str:
        truncated_context = self.truncate_context(context, self.max_context_tokens)
        context_messages = self.inject_context(messages, truncated_context)
        
        response = self.response(context_messages)
        
        if not self.validate_response_uses_context(response, truncated_context):
            logger.warning("Response doesn't seem to use the provided context. Requerying with emphasis.")
            response = self.requery_with_context_emphasis(context_messages, truncated_context)
        
        return response

    def run_function_calls(self, function_calls: List[FunctionCall], role: str = "function") -> List[Message]:
        results = []
        for function_call in function_calls:
            _function_call_timer = Timer()
            _function_call_timer.start()
            function_call.execute()
            _function_call_timer.stop()
            _function_call_message = Message(
                role=role,
                name=function_call.function.name,
                content=function_call.result,
                metrics={"time": _function_call_timer.elapsed},
            )
            if "function_call_times" not in self.metrics:
                self.metrics["function_call_times"] = {}
            if function_call.function.name not in self.metrics["function_call_times"]:
                self.metrics["function_call_times"][function_call.function.name] = []
            self.metrics["function_call_times"][function_call.function.name].append(_function_call_timer.elapsed)
            results.append(_function_call_message)
        return results