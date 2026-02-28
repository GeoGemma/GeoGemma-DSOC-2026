"""
Tool executor module for the GIS AI Agent.

This module provides functionality for executing tools, including support for
parallel execution, caching results, and building tool execution pipelines.
"""

import logging
import asyncio
import time
import json
import copy
from typing import Dict, Any, List, Optional, Callable, Tuple, Union, Set

from .cache import get_tool_result_cache, async_cached

# Configure logging
logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Manages the execution of tools, including caching and parallel execution.
    
    This class is responsible for:
    - Executing tools with proper error handling
    - Caching tool results to avoid redundant calls
    - Supporting parallel execution of multiple tools
    - Supporting sequential tool pipelines
    """
    
    def __init__(self, tools: Dict[str, Dict[str, Any]]):
        """
        Initialize the tool executor.
        
        Args:
            tools: Dictionary of available tools.
        """
        self.tools = tools
        self.cache = get_tool_result_cache()
        
        logger.info(f"ToolExecutor initialized with {len(tools)} tools")
    
    async def execute_tool(self, 
                         tool_name: str, 
                         arguments: Dict[str, Any],
                         use_cache: bool = True,
                         force_refresh: bool = False) -> Dict[str, Any]:
        """
        Execute a single tool.
        
        Args:
            tool_name: Name of the tool to execute.
            arguments: Arguments to pass to the tool.
            use_cache: Whether to use cached results if available.
            force_refresh: Whether to force a refresh of cached results.
            
        Returns:
            The tool result.
        """
        if tool_name not in self.tools:
            logger.error(f"Tool not found: {tool_name}")
            return {"error": f"Tool not found: {tool_name}"}
        
        tool = self.tools[tool_name]
        
        # Check cache if requested
        if use_cache and not force_refresh:
            cache_key = self._generate_cache_key(tool_name, arguments)
            cached_result = self.cache.get(cache_key)
            
            if cached_result is not None:
                logger.info(f"Using cached result for tool: {tool_name}")
                return cached_result
        
        # Execute the tool
        try:
            start_time = time.time()
            
            # Get the function from the tool
            tool_function = tool["function"]
            
            # Execute the function
            result = await tool_function(arguments)
            
            end_time = time.time()
            logger.info(f"Tool {tool_name} executed in {end_time - start_time:.2f}s")
            
            # Cache the result if required
            if use_cache:
                cache_key = self._generate_cache_key(tool_name, arguments)
                # Determine TTL based on tool type
                ttl = self._determine_cache_ttl(tool_name, result)
                self.cache.set(cache_key, result, ttl)
            
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def execute_parallel(self, 
                             tools: List[Tuple[str, Dict[str, Any]]],
                             use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Execute multiple tools in parallel.
        
        Args:
            tools: List of (tool_name, arguments) tuples.
            use_cache: Whether to use cached results if available.
            
        Returns:
            Dictionary mapping tool names to results.
        """
        tasks = []
        
        # Create a task for each tool
        for tool_name, arguments in tools:
            task = asyncio.create_task(
                self.execute_tool(tool_name, arguments, use_cache)
            )
            tasks.append((tool_name, task))
        
        # Wait for all tasks to complete
        results = {}
        for tool_name, task in tasks:
            try:
                result = await task
                results[tool_name] = result
            except Exception as e:
                logger.error(f"Error in parallel execution of {tool_name}: {e}")
                results[tool_name] = {"error": str(e)}
        
        return results
    
    async def execute_pipeline(self, 
                             pipeline: List[Dict[str, Any]],
                             use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Execute a pipeline of tools in sequence, where the output of one tool
        can be used as input to the next.
        
        Args:
            pipeline: List of pipeline steps, each with 'tool', 'arguments', and
                      optional 'output_mapping' for next steps.
            use_cache: Whether to use cached results if available.
            
        Returns:
            List of results from each step.
        """
        results = []
        context = {}  # For sharing data between steps
        
        for step in pipeline:
            tool_name = step["tool"]
            arguments = copy.deepcopy(step["arguments"])  # Copy to avoid modifying original
            
            # Replace placeholder arguments with values from the context
            self._apply_context_to_arguments(arguments, context)
            
            # Execute the tool
            result = await self.execute_tool(tool_name, arguments, use_cache)
            
            # Update the context with the result based on output_mapping
            if "output_mapping" in step and isinstance(step["output_mapping"], dict):
                for context_key, result_path in step["output_mapping"].items():
                    context[context_key] = self._get_nested_value(result, result_path)
            
            # Add the result to the list
            results.append({
                "tool": tool_name,
                "arguments": arguments,
                "result": result
            })
            
            # If this step failed and it's marked as required, stop the pipeline
            if "error" in result and step.get("required", True):
                logger.warning(f"Pipeline stopped at required step {tool_name} due to error")
                break
        
        return results
    
    def _generate_cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Generate a cache key for a tool call.
        
        Args:
            tool_name: Name of the tool.
            arguments: Arguments to the tool.
            
        Returns:
            A string cache key.
        """
        try:
            # Sort the arguments for consistent keys
            sorted_args = json.dumps(arguments, sort_keys=True)
            return f"tool:{tool_name}:{sorted_args}"
        except (TypeError, ValueError):
            # Fall back to string representation if JSON serialization fails
            return f"tool:{tool_name}:{str(arguments)}"
    
    def _determine_cache_ttl(self, tool_name: str, result: Dict[str, Any]) -> int:
        """
        Determine an appropriate TTL for a tool result based on the tool name and result.
        
        Args:
            tool_name: Name of the tool.
            result: Result of the tool execution.
            
        Returns:
            TTL in seconds.
        """
        # Default TTL (30 minutes)
        default_ttl = 1800
        
        # Adjust TTL based on tool name
        tool_ttl_map = {
            # Longer TTL for relatively static data
            "get_location_info": 86400,  # 24 hours
            "calculate_distance": 86400,  # 24 hours
            "find_nearby_features": 43200,  # 12 hours
            "analyze_area": 43200,  # 12 hours
            
            # Medium TTL for moderately changing data
            "get_carbon_footprint": 21600,  # 6 hours
            "analyze_water_resources": 21600,  # 6 hours
            "assess_biodiversity": 21600,  # 6 hours
            "analyze_land_use_change": 21600,  # 6 hours
            "calculate_environmental_risk": 21600,  # 6 hours
            
            # Shorter TTL for frequently updated data
            "get_current_weather": 1800,  # 30 minutes
            "get_weather_forecast": 3600,  # 1 hour
            "get_air_quality": 1800,  # 30 minutes
            
            # No caching for generation tools
            "generate_map": 0,
            "create_chart": 0,
            "create_comparison_visualization": 0,
            "answer_gis_question": 0
        }
        
        # Get TTL from map or use default
        ttl = tool_ttl_map.get(tool_name, default_ttl)
        
        # If there's an error in the result, reduce TTL
        if "error" in result:
            ttl = min(ttl, 300)  # 5 minutes max for errors
        
        return ttl
    
    def _apply_context_to_arguments(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Apply context values to arguments in-place.
        
        Args:
            arguments: Arguments to modify.
            context: Context values to apply.
        """
        for key, value in arguments.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Extract the context key
                context_key = value[2:-1]
                
                if context_key in context:
                    arguments[key] = context[context_key]
            elif isinstance(value, dict):
                self._apply_context_to_arguments(value, context)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._apply_context_to_arguments(item, context)
                    elif isinstance(item, str) and item.startswith("${") and item.endswith("}"):
                        context_key = item[2:-1]
                        if context_key in context:
                            value[i] = context[context_key]
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """
        Get a value from a nested dictionary using a dot-separated path.
        
        Args:
            obj: The dictionary to extract a value from.
            path: The path to the value, e.g. 'result.weather.temperature'.
            
        Returns:
            The extracted value, or None if not found.
        """
        parts = path.split('.')
        value = obj
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value


# Singleton instance
_tool_executor = None


def get_tool_executor(tools: Optional[Dict[str, Dict[str, Any]]] = None) -> ToolExecutor:
    """
    Get the tool executor instance.
    
    Args:
        tools: Dictionary of available tools. Only needed on first call.
        
    Returns:
        The tool executor instance.
    """
    global _tool_executor
    
    if _tool_executor is None:
        if tools is None:
            raise ValueError("Tools dictionary required for first initialization")
        
        _tool_executor = ToolExecutor(tools)
    
    return _tool_executor 