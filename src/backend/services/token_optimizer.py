import tiktoken

class TokenOptimizer:
    MAX_TOKENS = 4000  # Adjust based on your LLM's limits

    @staticmethod
    def optimize_context(context: str, query: str) -> str:
        total_tokens = TokenOptimizer.count_tokens(context) + TokenOptimizer.count_tokens(query)
        if total_tokens <= TokenOptimizer.MAX_TOKENS:
            return context

        max_context_tokens = TokenOptimizer.MAX_TOKENS - TokenOptimizer.count_tokens(query) - 100  # Buffer
        return TokenOptimizer.truncate_to_token_limit(context, max_context_tokens)

    @staticmethod
    def count_tokens(text: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

    @staticmethod
    def truncate_to_token_limit(text: str, max_tokens: int) -> str:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return encoding.decode(tokens[:max_tokens])