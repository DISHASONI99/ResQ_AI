"""
LLM Service - Portkey AI Gateway with multi-provider fallback

Supports:
- Groq (primary): llama-3.3-70b-versatile, gpt-oss-120b, llama-prompt-guard-2-86m
- Cerebras (fallback): llama-3.3-70b, gpt-oss-120b, qwen-3-32b, llama3.1-8b
- Google (backup): gemini-2.0-flash, gemini-1.5-pro

Portkey features:
- Automatic fallback between providers
- Response caching (90% cost savings)
- Request logging and analytics
- Rate limiting and retries
"""
from typing import Optional, Dict, Any, List
import json
import logging
import os

from src.config import settings

logger = logging.getLogger(__name__)


class PortkeyLLMService:
    """
    LLM service using Portkey AI Gateway.
    
    Uses Portkey Config (enterprise approach) instead of deprecated Virtual Keys.
    Config handles: fallback, semantic caching, retry, rate limiting.
    """
    
    # Tier to agent mapping
    AGENT_TIERS = {
        "supervisor": "fast",
        "geo": "fast",
        "protocol": "fast",
        "vision": "fast",
        "triage": "medium",
        "reflector": "heavy",
        "citation": "fast",
        "grounding": "fast",
    }
    
    def __init__(self):
        """Initialize Portkey client with Config ID."""
        self.portkey_api_key = os.getenv("PORTKEY_API_KEY", "")
        self.portkey_config_id = os.getenv("PORTKEY_CONFIG_ID", "")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")  # For direct fallback
        
        # Tier-specific configs (optional - falls back to main config)
        self.config_fast = os.getenv("PORTKEY_CONFIG_FAST", "")
        self.config_medium = os.getenv("PORTKEY_CONFIG_MEDIUM", "")
        self.config_heavy = os.getenv("PORTKEY_CONFIG_HEAVY", "")
        
        # Default settings
        self.temperature = getattr(settings, 'LLM_TEMPERATURE', 0.3)
        self.max_tokens = getattr(settings, 'LLM_MAX_TOKENS', 2048)
        
        # Check if Portkey is available
        self._portkey_available = bool(self.portkey_api_key and self.portkey_config_id)
        
        # Store Portkey clients for each tier
        self._portkey_clients = {}
        
        if self._portkey_available:
            self._setup_portkey()
        else:
            logger.warning("⚠️ PORTKEY_API_KEY or PORTKEY_CONFIG_ID not set, using direct Groq API")
    
    def _get_config_for_tier(self, tier: str) -> str:
        """Get the appropriate Portkey config ID for a tier."""
        mapping = {
            "fast": self.config_fast,
            "medium": self.config_medium,
            "heavy": self.config_heavy,
        }
        config = mapping.get(tier, "")
        # Fall back to main config if tier-specific not set
        return config if config else self.portkey_config_id
    
    def _get_portkey_client(self, tier: str = "default"):
        """Get or create a Portkey client for the specified tier."""
        if tier not in self._portkey_clients:
            from portkey_ai import Portkey
            config_id = self._get_config_for_tier(tier) if tier != "default" else self.portkey_config_id
            self._portkey_clients[tier] = Portkey(
                api_key=self.portkey_api_key,
                config=config_id,
            )
            logger.info(f"   Created Portkey client for tier '{tier}' with config: {config_id[:20]}...")
        return self._portkey_clients[tier]
    
    def _setup_portkey(self):
        """Setup Portkey client with Config (handles fallback, cache, retry)."""
        try:
            from portkey_ai import Portkey
            
            # Initialize with Config ID (enterprise approach)
            # Config includes: fallback chain, semantic cache, retry logic
            self.portkey = Portkey(
                api_key=self.portkey_api_key,
                config=self.portkey_config_id,
            )
            
            logger.info("✅ Portkey AI Gateway initialized")
            logger.info(f"   Config: {self.portkey_config_id}")
            logger.info(f"   Features: Fallback → Semantic Cache → Retry")
            
        except ImportError:
            logger.warning("portkey-ai package not installed, falling back to direct API")
            self._portkey_available = False
        except Exception as e:
            logger.error(f"Failed to initialize Portkey: {e}")
            self._portkey_available = False
    
    def _build_portkey_model(self, provider: str = None, model: str = None) -> str:
        """
        Build model string for Portkey.
        
        With Config, we don't need to specify model - Config handles routing.
        This method is kept for compatibility but returns None to use Config defaults.
        """
        # Config handles model selection, return None to use Config defaults
        return None
    
    async def generate(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        use_fallback: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate LLM response using Portkey with automatic fallback.
        
        Args:
            user_prompt: User message
            system_prompt: System message (optional)
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: {"type": "json_object"} for structured output
            model: Override default model
            provider: Force specific provider (groq, cerebras, google)
            use_fallback: If True, try fallback models on failure
            
        Returns:
            {"content": str, "model": str, "provider": str, "usage": dict}
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_prompt})
        
        # Use Portkey if available
        if self._portkey_available:
            return await self._generate_with_portkey(
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format=response_format,
                model=model,
                provider=provider,
                use_fallback=use_fallback,
            )
        else:
            # Fallback to direct API
            return await self._generate_direct(
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format=response_format,
            )
    
    async def generate_with_tier(
        self,
        agent_name: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Generate LLM response using tier-specific Portkey config.
        
        Automatically routes to appropriate model tier based on agent:
        - fast (8B): supervisor, geo, protocol, vision
        - medium (32B): triage
        - heavy (70B): reflector
        
        Args:
            agent_name: Name of the calling agent (e.g., "triage", "supervisor")
            user_prompt: User message
            system_prompt: System message (optional)
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: {"type": "json_object"} for structured output
            
        Returns:
            {"content": str, "model": str, "provider": str, "tier": str, "usage": dict}
        """
        tier = self.AGENT_TIERS.get(agent_name.lower(), "heavy")
        logger.info(f"🎯 Agent '{agent_name}' using tier '{tier}'")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        if not self._portkey_available:
            result = await self._generate_direct(
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format=response_format,
            )
            result["tier"] = tier
            return result
        
        try:
            client = self._get_portkey_client(tier)
            
            api_params = {
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }
            
            if response_format:
                api_params["response_format"] = response_format
            
            response = client.chat.completions.create(**api_params)
            
            model_used = getattr(response, 'model', f'{tier}-routed')
            
            logger.info(f"✅ Tier '{tier}' success via Portkey")
            
            return {
                "content": response.choices[0].message.content,
                "model": model_used,
                "provider": f"portkey-{tier}",
                "tier": tier,
                "usage": {
                    "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                    "total_tokens": getattr(response.usage, 'total_tokens', 0),
                },
                "cached": hasattr(response, '_portkey_cache_status'),
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Tier '{tier}' failed: {e}, falling back to main config")
            # Fall back to main generate method
            result = await self.generate(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            result["tier"] = tier
            return result
    
    async def _generate_with_portkey(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        use_fallback: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate using Portkey with Config-based routing.
        
        Config handles: fallback, semantic caching, retry automatically.
        """
        try:
            logger.info("🔄 Calling Portkey (Config handles routing)...")
            
            # Build API call parameters
            api_params = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            # Add response_format if specified (for JSON mode)
            if response_format:
                api_params["response_format"] = response_format
            
            # Call Portkey - Config handles model selection and fallback
            response = self.portkey.chat.completions.create(**api_params)
            
            # Extract model info from response
            model_used = getattr(response, 'model', 'config-routed')
            
            logger.info(f"✅ Success via Portkey Config")
            
            return {
                "content": response.choices[0].message.content,
                "model": model_used,
                "provider": "portkey-config",
                "usage": {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                } if hasattr(response, "usage") else {},
            }
            
        except Exception as e:
            error_str = str(e)
            
            # Check for Portkey guardrail errors
            if "446" in error_str:
                logger.error(f"🛡️ Guardrail blocked input: {error_str}")
                raise ValueError(
                    "Your message was flagged for safety. "
                    "Please rephrase and avoid inappropriate content."
                )
            
            elif "246" in error_str:
                logger.error(f"🛡️ Guardrail blocked output: {error_str}")
                raise ValueError(
                    "Response failed safety check. Please try rephrasing your request."
                )
            
            else:
                logger.error(f"❌ Portkey failed: {e}")
                raise RuntimeError(f"LLM generation failed: {e}")
    
    async def _generate_direct(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Direct Groq API call (fallback when Portkey unavailable)."""
        import httpx
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "content": data["choices"][0]["message"]["content"],
                "model": data["model"],
                "provider": "groq",
                "usage": data.get("usage", {}),
            }
    
    async def generate_structured(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate JSON-structured response.
        Parses the content as JSON and returns it.
        """
        response = await self.generate(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
            **kwargs,
        )
        
        try:
            content = json.loads(response["content"])
            return {
                "content": content,
                "model": response["model"],
                "provider": response.get("provider", "unknown"),
                "usage": response["usage"],
            }
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON: {response['content'][:200]}")
            return response
    



# Singleton for backward compatibility
_llm_service: Optional[PortkeyLLMService] = None


def get_llm_service() -> PortkeyLLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = PortkeyLLMService()
    return _llm_service


# Alias for backward compatibility
LLMService = PortkeyLLMService
