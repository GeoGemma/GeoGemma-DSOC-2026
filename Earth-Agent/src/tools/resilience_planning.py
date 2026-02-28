"""
Resilience planning tools for the GIS AI Agent.

This module provides tools for assessing disaster risks, infrastructure vulnerabilities,
planning adaptation measures, and evaluating community resilience.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
import asyncio

from ..config import get_config
from ..data_sources.earth_engine_connector import get_earth_engine_client
from ..data_sources.openweathermap_connector import get_openweathermap_client

# Configure logging
logger = logging.getLogger(__name__)


async def assess_disaster_risk(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess disaster risk for a specific area.

    Args:
        arguments: Dictionary containing:
            - area: Area name, coordinates, or GeoJSON polygon.
            - hazard_types: Types of hazards to assess (flood, drought, etc., or "all").
            - time_frame: Time frame for risk assessment (current, 2030, 2050, 2100).
            - climate_scenario: Future climate scenario to consider (RCP2.6, RCP4.5, etc.).
            - include_socioeconomic: Whether to include socioeconomic vulnerability factors.

    Returns:
        Dictionary with disaster risk assessment results.
    """
    try:
        # Extract arguments
        area = arguments.get("area", "")
        hazard_types = arguments.get("hazard_types", ["all"])
        time_frame = arguments.get("time_frame", "current")
        climate_scenario = arguments.get("climate_scenario", "RCP4.5")
        include_socioeconomic = arguments.get("include_socioeconomic", True)
        
        # Validate arguments
        if not area:
            return {"error": "Area is required"}
        
        # Get Earth Engine client - this now returns directly without awaiting
        ee_client = await get_earth_engine_client()
        
        # Call Earth Engine connector to assess disaster risk
        risk_data = await ee_client.assess_disaster_risk(
            area=area,
            hazard_types=hazard_types,
            time_frame=time_frame,
            climate_scenario=climate_scenario,
            include_socioeconomic=include_socioeconomic
        )
        
        # Return the results
        return {
            "success": True,
            "risk_assessment": risk_data,
            "message": f"Disaster risk assessed for {area} with time frame {time_frame}"
        }
    
    except Exception as e:
        logger.error(f"Error assessing disaster risk: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to assess disaster risk"
        }


async def evaluate_infrastructure_vulnerability(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate infrastructure vulnerability to climate hazards.

    Args:
        arguments: Dictionary containing:
            - area: Area name, coordinates, or GeoJSON polygon.
            - infrastructure_types: Types of infrastructure to evaluate (transportation, energy, etc., or "all").
            - hazard_types: Types of hazards to consider (flood, extreme_weather, etc., or "all").
            - time_horizon: Time horizon for the assessment (current, 2030, 2050, 2100).
            - include_interdependencies: Whether to include infrastructure system interdependencies.

    Returns:
        Dictionary with infrastructure vulnerability assessment.
    """
    try:
        # Extract arguments
        area = arguments.get("area", "")
        infrastructure_types = arguments.get("infrastructure_types", ["all"])
        hazard_types = arguments.get("hazard_types", ["all"])
        time_horizon = arguments.get("time_horizon", "current")
        include_interdependencies = arguments.get("include_interdependencies", False)
        
        # Validate arguments
        if not area:
            return {"error": "Area is required"}
        
        # Get Earth Engine client - this now returns directly without awaiting
        ee_client = await get_earth_engine_client()
        
        # Call Earth Engine connector to evaluate infrastructure vulnerability
        vulnerability_data = await ee_client.evaluate_infrastructure_vulnerability(
            area=area,
            infrastructure_types=infrastructure_types,
            hazard_types=hazard_types,
            time_horizon=time_horizon,
            include_interdependencies=include_interdependencies
        )
        
        # Return the results
        return {
            "success": True,
            "vulnerability_assessment": vulnerability_data,
            "message": f"Infrastructure vulnerability evaluated for {area} with time horizon {time_horizon}"
        }
    
    except Exception as e:
        logger.error(f"Error evaluating infrastructure vulnerability: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to evaluate infrastructure vulnerability"
        }


async def design_adaptation_measures(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Design adaptation measures for climate resilience.

    Args:
        arguments: Dictionary containing:
            - area: Area name, coordinates, or GeoJSON polygon.
            - risk_types: Types of risks to address (flood, drought, etc., or "all").
            - priority_sectors: Priority sectors for adaptation (urban, agriculture, etc., or "all").
            - time_frame: Time frame for adaptation measures (short-term, medium-term, long-term).
            - constraints: Constraints to consider in adaptation planning (budget, technical, social).

    Returns:
        Dictionary with adaptation measures design.
    """
    try:
        # Extract arguments
        area = arguments.get("area", "")
        risk_types = arguments.get("risk_types", ["all"])
        priority_sectors = arguments.get("priority_sectors", ["all"])
        time_frame = arguments.get("time_frame", "medium-term")
        constraints = arguments.get("constraints", {
            "budget": "medium",
            "technical": "medium",
            "social": "medium"
        })
        
        # Validate arguments
        if not area:
            return {"error": "Area is required"}
        
        # Get Earth Engine client - this now returns directly without awaiting
        ee_client = await get_earth_engine_client()
        
        # Call Earth Engine connector to design adaptation measures
        adaptation_data = await ee_client.design_adaptation_measures(
            area=area,
            risk_types=risk_types,
            priority_sectors=priority_sectors,
            time_frame=time_frame,
            constraints=constraints
        )
        
        # Return the results
        return {
            "success": True,
            "adaptation_measures": adaptation_data,
            "message": f"Adaptation measures designed for {area} with {time_frame} time frame"
        }
    
    except Exception as e:
        logger.error(f"Error designing adaptation measures: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to design adaptation measures"
        }


async def assess_community_resilience(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess community resilience to climate change.

    Args:
        arguments: Dictionary containing:
            - community: Community name, coordinates, or GeoJSON polygon.
            - indicators: Resilience indicators to assess (social_capital, economic_resources, etc., or "all").
            - hazard_focus: Specific hazards to focus on (flood, drought, etc., or "all").
            - include_demographics: Whether to include demographic factors.
            - comparison_regions: Regions to compare with (optional).

    Returns:
        Dictionary with community resilience assessment.
    """
    try:
        # Extract arguments
        community = arguments.get("community", "")
        indicators = arguments.get("indicators", ["all"])
        hazard_focus = arguments.get("hazard_focus", ["all"])
        include_demographics = arguments.get("include_demographics", True)
        comparison_regions = arguments.get("comparison_regions", [])
        
        # Validate arguments
        if not community:
            return {"error": "Community is required"}
        
        # Get Earth Engine client - this now returns directly without awaiting
        ee_client = await get_earth_engine_client()
        
        # Call Earth Engine connector to assess community resilience
        resilience_data = await ee_client.assess_community_resilience(
            community=community,
            indicators=indicators,
            hazard_focus=hazard_focus,
            include_demographics=include_demographics,
            comparison_regions=comparison_regions
        )
        
        # Return the results
        return {
            "success": True,
            "resilience_assessment": resilience_data,
            "message": f"Community resilience assessed for {community}"
        }
    
    except Exception as e:
        logger.error(f"Error assessing community resilience: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to assess community resilience"
        }


# Export all tools
resilience_planning_tools = {
    "assess_disaster_risk": {
        "function": assess_disaster_risk,
        "description": "Assess disaster risk for a specific area",
        "parameters": {
            "area": "Area name, coordinates, or GeoJSON polygon",
            "hazard_types": "Types of hazards to assess (flood, drought, etc., or 'all')",
            "time_frame": "Time frame for risk assessment (current, 2030, 2050, 2100)",
            "climate_scenario": "Future climate scenario to consider (RCP2.6, RCP4.5, etc.)",
            "include_socioeconomic": "Whether to include socioeconomic vulnerability factors"
        }
    },
    "evaluate_infrastructure_vulnerability": {
        "function": evaluate_infrastructure_vulnerability,
        "description": "Evaluate infrastructure vulnerability to climate hazards",
        "parameters": {
            "area": "Area name, coordinates, or GeoJSON polygon",
            "infrastructure_types": "Types of infrastructure to evaluate (transportation, energy, etc., or 'all')",
            "hazard_types": "Types of hazards to consider (flood, extreme_weather, etc., or 'all')",
            "time_horizon": "Time horizon for the assessment (current, 2030, 2050, 2100)",
            "include_interdependencies": "Whether to include infrastructure system interdependencies"
        }
    },
    "design_adaptation_measures": {
        "function": design_adaptation_measures,
        "description": "Design adaptation measures for climate resilience",
        "parameters": {
            "area": "Area name, coordinates, or GeoJSON polygon",
            "risk_types": "Types of risks to address (flood, drought, etc., or 'all')",
            "priority_sectors": "Priority sectors for adaptation (urban, agriculture, etc., or 'all')",
            "time_frame": "Time frame for adaptation measures (short-term, medium-term, long-term)",
            "constraints": "Constraints to consider in adaptation planning (budget, technical, social)"
        }
    },
    "assess_community_resilience": {
        "function": assess_community_resilience,
        "description": "Assess community resilience to climate change",
        "parameters": {
            "community": "Community name, coordinates, or GeoJSON polygon",
            "indicators": "Resilience indicators to assess (social_capital, economic_resources, etc., or 'all')",
            "hazard_focus": "Specific hazards to focus on (flood, drought, etc., or 'all')",
            "include_demographics": "Whether to include demographic factors",
            "comparison_regions": "Regions to compare with (optional)"
        }
    }
} 