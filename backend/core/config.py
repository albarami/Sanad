"""
Configuration management for Sanad v2.
Loads configuration from YAML files and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import re


class LLMConfig(BaseModel):
    """Configuration for a specific LLM provider."""
    model: str
    temperature: float = 0.3
    max_tokens: int = 150
    timeout: float = 3.0


class LLMSettings(BaseModel):
    """LLM configuration settings."""
    primary_provider: str = "openai"
    fallback_provider: str = "anthropic"
    openai: LLMConfig
    anthropic: LLMConfig


class AgentWeights(BaseModel):
    """Weights for different agents."""
    integrity: float = 0.4
    precision: float = 0.3
    provenance: float = 0.2
    domain: float = 0.1


class Thresholds(BaseModel):
    """Various threshold values."""
    trigger_similarity: float = 0.72
    enhancement_threshold: float = 0.70
    high_confidence: float = 0.85
    # Retry configuration for LLM calls
    max_retries: int = 2
    base_delay: float = 1.0


class RetrievalConfig(BaseModel):
    """Retrieval configuration."""
    top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 100


class DomainConfig(BaseModel):
    """Domain-specific configuration for different contexts."""
    name: str = "general"
    keywords: list[str] = []
    enhancement_instructions: str = ""  # Default empty to prevent blank line issues
    terminology_guidelines: str = ""
    source_requirements: str = ""


class PerformanceTargets(BaseModel):
    """Performance target metrics."""
    max_latency_ms: int = 1000
    target_retrieval_ms: int = 10


class Config(BaseModel):
    """Main configuration class."""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    llm: LLMSettings
    agent_weights: AgentWeights
    thresholds: Thresholds
    retrieval: RetrievalConfig
    performance: PerformanceTargets
    domain: DomainConfig = Field(default_factory=DomainConfig)
    
    # Additional settings from environment
    environment: str = Field(default="development")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8080)
    database_url: str = Field(default="sqlite:///./sanad.db")
    log_level: str = Field(default="INFO")


class ConfigLoader:
    """Loads and manages configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_path: Path to the configuration file. If None, looks for config/config.yaml
        """
        # Load environment variables
        load_dotenv()
        
        # Determine config path
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"
        
        self.config_path = config_path
        self._config: Optional[Config] = None
    
    def _substitute_env_vars(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively substitute environment variables in the configuration.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configuration with environment variables substituted
        """
        def substitute_value(value):
            if isinstance(value, str):
                # Look for ${VAR_NAME} pattern
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, value)
                for var_name in matches:
                    env_value = os.getenv(var_name)
                    if env_value:
                        value = value.replace(f'${{{var_name}}}', env_value)
                return value
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        return substitute_value(config_dict)
    
    def load(self) -> Config:
        """
        Load configuration from file and environment variables.
        
        Returns:
            Config object
        """
        if self._config is not None:
            return self._config
        
        # Load YAML configuration
        with open(self.config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Substitute environment variables
        config_dict = self._substitute_env_vars(config_dict)
        
        # Override with direct environment variables
        env_overrides = {
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'api_host': os.getenv('API_HOST', '0.0.0.0'),
            'api_port': int(os.getenv('API_PORT', '8080')),
            'database_url': os.getenv('DATABASE_URL', 'sqlite:///./sanad.db'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        }
        
        # Merge configurations
        config_dict.update(env_overrides)
        
        # Create config object
        self._config = Config(**config_dict)
        
        return self._config
    
    def reload(self) -> Config:
        """
        Reload configuration from file.
        
        Returns:
            Updated Config object
        """
        self._config = None
        return self.load()


# Global configuration instance
_config_loader: Optional[ConfigLoader] = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Returns:
        Config object
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.load()


def reload_config() -> Config:
    """
    Reload the global configuration.
    
    Returns:
        Updated Config object
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.reload() 