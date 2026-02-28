from flask import request, jsonify
import logging
import ee
import json
import re
from datetime import datetime, timedelta
# Import the new functions at the top of api.py
from services.dataset_service import (
    process_dataset_for_visualization,
    get_spatial_extent,
    get_lookat,
    get_feature_properties,
    extract_visualization_params,
    get_date_range,
    get_best_scale_for_dataset,         # New import
    apply_temporal_filter_to_collection, # New import
    get_image_from_collection          # New import
)

from services.earth_engine import (
    filter_open_buildings,
    create_feature_collection_image,
    handle_open_buildings_temporal_visualization,
    handle_worldcover_visualization,
    handle_sentinel1_visualization
)

logger = logging.getLogger(__name__)

# Available colormaps - server-side definitions
COLORMAPS = {
    'terrain': ['#0A42A5', '#00D300', '#FFFF00', '#FF8C00', '#A52A2A', '#FFFFFF'],
    'jet': ['#000080', '#0000FF', '#00FFFF', '#FFFF00', '#FF0000', '#800000'],
    'plasma': ['#0D0887', '#5B02A3', '#9A179B', '#CB4678', '#EB7852', '#FDB32F', '#F0F921'],
    'blues': ['#F7FBFF', '#D0D1E6', '#A6BDDB', '#74A9CF', '#3690C0', '#0570B0', '#034E7B'],
    'greens': ['#F7FCF5', '#C7E9C0', '#A1D99B', '#74C476', '#41AB5D', '#238B45', '#005A32']
}

def register_api_routes(app, embedding_manager):
    """Register API routes for the application"""
    
    # Register the value retrieval route
    register_value_retrieval_route(app, embedding_manager)
    
    @app.route('/search_datasets', methods=['POST'])
    def search_datasets():
        data = request.get_json()
        query = data.get('query', '')
        
        # New parameters for controlling search behavior
        top_k = data.get('top_k', 20)
        expand_query = data.get('expand_query', True)
        
        # New parameters for search weights
        custom_weights = data.get('weights', None)
        if custom_weights and isinstance(custom_weights, dict):
            try:
                # Update search weights if provided
                embedding_manager.enhanced_search.update_weights(custom_weights)
                logger.info(f"Using custom search weights: {custom_weights}")
            except Exception as e:
                logger.warning(f"Error updating search weights: {e}")
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        logger.info(f"Searching datasets with query: {query}")
        
        try:
            # Use enhanced search with more results
            results = embedding_manager.retrieve_datasets(query, top_k=top_k)
            
            # Add debugging for the results
            logger.info(f"Retrieved {len(results)} datasets from search")
            
            processed_results = []
            # Extract the palette from each dataset's summaries and add preview image path
            for result in results:
                try:
                    # Get dataset ID for the preview image filename
                    dataset_id = result.get('id', '')
                    if not dataset_id:
                        logger.warning(f"Missing dataset ID in result: {result}")
                        continue
                        
                    image_id = dataset_id.replace('/', '_') if '/' in dataset_id else dataset_id
                    
                    # Create a copy of the result to modify
                    processed_result = result.copy()
                    
                    # Set the preview image path
                    logger.info(f"Processing dataset: {dataset_id}")
                    processed_result['preview_url'] = f"static/preview_images/{image_id}.png"
                    
                    # Try to get palette from different potential locations
                    palette = None
                    try:
                        # Extract colors from gee:classes
                        if ('summaries' in result and 
                            'eo:bands' in result.get('summaries', {}) and 
                            result.get('summaries', {}).get('eo:bands')):
                            
                            gee_classes = result.get('summaries', {}).get('eo:bands', [])[0].get('gee:classes', [])
                            if gee_classes and isinstance(gee_classes, list):
                                palette = [item.get('color', '') for item in gee_classes if 'color' in item]
                                # Add '#' prefix if colors don't have it
                                palette = ['#' + color if not color.startswith('#') else color 
                                        for color in palette if color]
                    except Exception as e:
                        logger.warning(f"Error extracting palette for {dataset_id}: {str(e)}")
                        palette = None
                    
                    processed_result['palette'] = palette
                    
                    # Also store class descriptions if available
                    try:
                        if ('summaries' in result and 
                            'eo:bands' in result.get('summaries', {}) and 
                            result.get('summaries', {}).get('eo:bands')):
                            
                            gee_classes = result.get('summaries', {}).get('eo:bands', [])[0].get('gee:classes', [])
                            processed_result['class_descriptions'] = gee_classes
                    except Exception as e:
                        logger.warning(f"Error extracting class descriptions for {dataset_id}: {str(e)}")
                        processed_result['class_descriptions'] = None
                        
                    # Add GEE type if available for filtering
                    if 'gee:type' in result:
                        processed_result['type'] = result['gee:type']
                        
                    # Extract and add keywords if available for display
                    keywords = []
                    if 'summaries' in result:
                        summaries = result.get('summaries', {})
                        if 'keywords' in summaries and isinstance(summaries.get('keywords', []), list):
                            keywords.extend(summaries.get('keywords', []))
                        if 'gee:terms' in summaries and isinstance(summaries.get('gee:terms', []), list):
                            keywords.extend(summaries.get('gee:terms', []))
                            
                    if 'properties' in result and 'keywords' in result.get('properties', {}):
                        props_keywords = result.get('properties', {}).get('keywords', [])
                        if isinstance(props_keywords, list):
                            keywords.extend(props_keywords)
                        elif isinstance(props_keywords, str):
                            keywords.extend([k.strip() for k in props_keywords.split(',')])
                    
                    processed_result['keywords'] = list(set(keywords)) if keywords else []  # Remove duplicates
                    
                    # Add to processed results
                    processed_results.append(processed_result)
                    
                except Exception as e:
                    logger.error(f"Error processing search result {dataset_id if 'dataset_id' in locals() else 'unknown'}: {str(e)}")
                    # Continue processing other results
                    continue
            
            logger.info(f"Successfully processed {len(processed_results)} out of {len(results)} matching datasets")
            return jsonify({'results': processed_results})
        except Exception as e:
            logger.error(f"Error in search_datasets: {str(e)}")
            logger.exception("Full traceback for search error")
            return jsonify({'error': str(e)}), 500


    @app.route('/update_search_model', methods=['POST'])
    def update_search_model():
        """
        Update the search model configuration
        """
        data = request.get_json()
        model_size = data.get('model_size', 'small')
        use_enhanced_search = data.get('use_enhanced_search', True)
        
        try:
            # Update the embedding manager configuration
            embedding_manager.set_search_method(
                use_enhanced_search=use_enhanced_search,
                model_size=model_size
            )
            
            return jsonify({
                'success': True,
                'message': f"Search model updated to: {'enhanced' if use_enhanced_search else 'legacy'} with size {model_size}"
            })
        except Exception as e:
            logger.error(f"Error updating search model: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/update_search_weights', methods=['POST'])
    def update_search_weights():
        """
        Update the field weights for enhanced search
        """
        data = request.get_json()
        weights = data.get('weights', {})
        
        # Validate weights
        required_fields = ['title', 'id', 'description', 'keywords']
        for field in required_fields:
            if field not in weights:
                return jsonify({
                    'error': f"Missing required field in weights: {field}"
                }), 400
        
        try:
            # Check if using enhanced search
            if not hasattr(embedding_manager, 'enhanced_search') or embedding_manager.enhanced_search is None:
                return jsonify({
                    'error': "Enhanced search is not enabled. Enable it first via /update_search_model"
                }), 400
            
            # Update weights
            embedding_manager.enhanced_search.update_weights(weights)
            
            return jsonify({
                'success': True,
                'message': f"Search weights updated: {weights}"
            })
        except Exception as e:
            logger.error(f"Error updating search weights: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/search_info', methods=['GET'])
    def search_info():
        """
        Get information about the current search configuration
        """
        try:
            # Get current search method and model info
            use_enhanced = getattr(embedding_manager, 'use_enhanced_search', False)
            model_size = getattr(embedding_manager, 'model_size', 'small')
            
            # Get model details
            models = {
                'small': {
                    'embedding': 'BAAI/bge-small-en-v1.5',
                    'llm': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
                    'size_mb': {'embedding': 134, 'llm': 800}
                },
                'medium': {
                    'embedding': 'BAAI/bge-base-en-v1.5',
                    'llm': 'microsoft/phi-2',
                    'size_mb': {'embedding': 438, 'llm': 2700}
                },
                'large': {
                    'embedding': 'BAAI/bge-large-en-v1.5',
                    'llm': 'google/gemma-2b-it',
                    'size_mb': {'embedding': 1340, 'llm': 4800}
                }
            }
            
            # Get current weights if using enhanced search
            weights = {}
            if use_enhanced and hasattr(embedding_manager, 'enhanced_search') and embedding_manager.enhanced_search is not None:
                weights = embedding_manager.enhanced_search.weights
            
            return jsonify({
                'use_enhanced_search': use_enhanced,
                'model_size': model_size,
                'model_details': models.get(model_size, {}),
                'field_weights': weights,
                'dataset_count': len(embedding_manager.datasets) if embedding_manager.datasets else 0
            })
        except Exception as e:
            logger.error(f"Error getting search info: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
 
    @app.route('/get_tile', methods=['POST'])
    def get_tile():
        data = request.get_json()
        dataset_id = data.get('dataset_id')
        #dataset_id = dataset_id.replace('/', '_') if '/' in dataset_id else dataset_id

        if not dataset_id:
            return jsonify({'error': 'No dataset_id provided'}), 400
        
        logger.info(f"Getting tiles for dataset: {dataset_id}")
        
        # Special parameters that might be passed from frontend
        limit_features = data.get('limit_features', 5000)  # Default to 5000 features
        skip_confidence_filter = data.get('skip_confidence_filter', False)
        
        # Check for custom visualization parameters (band + colormap)
        visualization = data.get('visualization', None)
        
        # Check for temporal filter
        temporal_filter = None
        if visualization and 'temporal_filter' in visualization:
            temporal_filter = visualization['temporal_filter']
            logger.info(f"Custom temporal filter received: {json.dumps(temporal_filter)}")
        elif data.get('temporal_filter'):
            temporal_filter = data.get('temporal_filter')
            logger.info(f"Direct temporal filter received: {json.dumps(temporal_filter)}")
        
        # Debug: log if visualization params were provided
        if visualization:
            logger.info(f"Custom visualization params received: {json.dumps(visualization)}")
        
        # Find the dataset by its id.
        dataset = next((embedding_manager.datasets[d] for d in embedding_manager.datasets if embedding_manager.datasets[d]['id'] == dataset_id), None)
        if not dataset:
            logger.error(f"Dataset not found: {dataset_id}")
            return jsonify({'error': 'Dataset not found'}), 404
        
        try:
            # Process the dataset for visualization
            gee_collection = dataset.get('gee_id', dataset['id'])
            gee_type = dataset.get('gee:type', 'image_collection')
            

             # Override type for known datasets that are incorrectly labeled
            if dataset_id in ['Germany/Brandenburg/orthos/20cm', 'IGN/RGE_ALTI/1M']:
                gee_type = 'image'
                logger.info(f"Overriding dataset type to 'image' for {dataset_id}")
     

            # Identify dataset type for better temporal filtering and logging
            is_modis = 'MODIS' in gee_collection
            is_time_series = is_modis or any(x in gee_collection for x in ['VIIRS', 'GOES', 'GLDAS', 'TROPOMI'])
            is_landsat_sentinel = any(x in gee_collection for x in ['LANDSAT', 'SENTINEL', 'COPERNICUS'])
            
            if is_time_series:
                logger.info(f"Time series dataset detected: {gee_collection}")
            elif is_landsat_sentinel:
                logger.info(f"Spatial/composite dataset detected: {gee_collection}")
            
            # Log JS visualization info if available
            js_info = dataset.get('js_visualization_info', {})
            if 'temporal_filter' in js_info:
                tf = js_info['temporal_filter']
                logger.info(f"Temporal filter details:")
                logger.info(f"  Start date: {tf.get('start_date')}")
                logger.info(f"  End date: {tf.get('end_date')}")
                logger.info(f"  Filter method: {tf.get('filter_method')}")
                logger.info(f"  Start param raw: {tf.get('start_param_raw', 'Not specified')}")
                logger.info(f"  End param raw: {tf.get('end_param_raw', 'Not specified')}")
            
            # Get optimized date range using the improved function
            # If temporal filter is provided, use it instead of default
            if temporal_filter and 'start_date' in temporal_filter and 'end_date' in temporal_filter:
                date_range = [temporal_filter['start_date'], temporal_filter['end_date']]
                logger.info(f"Using custom temporal filter date range: {date_range}")
            else:
                date_range = get_date_range(dataset)
                logger.info(f"Using optimized date range: {date_range}")
            
            # Special handling for datasets known to have date range issues
            if dataset_id in ['FAO/SOFO/1/FPP', 'AU/GA/AUSTRALIA_5M_DEM', 'COPERNICUS/DEM']:
                date_range = ['1950-01-01', '2025-12-31']
                logger.info(f"Using special wide date range for dataset with date issues: {date_range}")



            # Extract visualization parameters
            # If custom visualization is provided, override the default parameters
            if visualization:
                # Handle custom band visualization
                vis_params = {}
                
                # Set the band
                selected_band = visualization.get('band')
                if selected_band:
                    vis_params['bands'] = [selected_band]
                
                # Set min/max values
                vis_params['min'] = visualization.get('min', 0)
                vis_params['max'] = visualization.get('max', 3000)
                
                # Log the custom min/max values
                logger.info(f"Using custom min/max: {vis_params['min']} to {vis_params['max']}")
                
                # Set palette based on the colormap
                colormap_id = visualization.get('colormap')
                if colormap_id and colormap_id in COLORMAPS:
                    vis_params['palette'] = COLORMAPS[colormap_id]
                elif 'colormap_colors' in visualization:
                    vis_params['palette'] = visualization['colormap_colors']
                
                # Add temporal filter if provided
                if 'temporal_filter' in visualization:
                    vis_params['temporal_filter'] = visualization['temporal_filter']
                
                # Log the custom visualization parameters
                logger.info(f"Using custom visualization parameters: {vis_params}")
                
                # Set default values for other parameters
                bands = vis_params.get('bands', [])
                palette = vis_params.get('palette', [])
                class_descriptions = None
            else:
                # Use default visualization parameters
                vis_params, bands, palette, class_descriptions = extract_visualization_params(dataset)
            
            # Get spatial information
            bbox = get_spatial_extent(dataset)
            lookat = get_lookat(dataset)
            
            # Default color for FeatureCollections if no palette is specified
            if gee_type.lower() == 'table' and not palette:
                vis_params['palette'] = ['#FF0000']  # Default to red for buildings/features
            
            logger.info(f"Visualization parameters: {vis_params}")
            
            # Handle different dataset types
            if gee_type.lower() == 'table':
                # This is a FeatureCollection (Table in GEE catalog)
                try:
                    features = ee.FeatureCollection(gee_collection)
                    logger.info("Successfully created FeatureCollection reference")
                except Exception as e:
                    logger.error(f"Error creating FeatureCollection: {str(e)}")
                    return jsonify({'error': f'Failed to create FeatureCollection reference: {str(e)}'}), 500

                # Check if custom style was requested
                if 'style' in data:
                    logger.info("Using custom styling parameters from request")
                    style_params = data['style']
                    # Update vis_params with style parameters
                    for key, value in style_params.items():
                        vis_params[key] = value
                    
                    logger.info(f"Applied custom style: {vis_params}")

                # Special handling for Open Buildings dataset
                if 'open-buildings' in gee_collection:
                    logger.info("Detected Open Buildings dataset, applying special handling")
                    try:
                        features = filter_open_buildings(
                            features, 
                            skip_confidence_filter=skip_confidence_filter, 
                            limit=limit_features
                        )
                    except Exception as e:
                        logger.error(f"Error filtering Open Buildings: {str(e)}")
                        return jsonify({'error': f'Error filtering Open Buildings: {str(e)}'}), 500

                # Create an image from the features for visualization
                try:
                    image, updated_vis_params = create_feature_collection_image(features, gee_collection, vis_params)
                    map_id_dict = image.getMapId(updated_vis_params)
                    is_feature_collection = True
                except Exception as e:
                    logger.error(f"Error generating map tiles for features: {str(e)}")
                    return jsonify({'error': f'Error generating map tiles: {str(e)}'}), 500
                
            elif gee_type.lower() == 'image':
                # Handle single image
                logger.info(f"Processing Image: {gee_collection}")
                try:
                    image = ee.Image(gee_collection)
                    
                    # Auto-detect RGB visualization if we have 3 bands but no palette
                    if 'bands' in vis_params and len(vis_params['bands']) == 3 and 'palette' not in vis_params:
                        logger.info(f"Detected potential RGB bands for image: {vis_params['bands']}")
                        # Create a copy of vis_params without modifying the original
                        rgb_vis_params = vis_params.copy()
                        
                        # Set appropriate visualization for RGB
                        # Remove any potential min/max values that might be inappropriate for RGB
                        if 'min' in rgb_vis_params:
                            rgb_vis_params['min'] = [rgb_vis_params['min']] * 3 if not isinstance(rgb_vis_params['min'], list) else rgb_vis_params['min']
                        else:
                            rgb_vis_params['min'] = [0, 0, 0]
                            
                        if 'max' in rgb_vis_params:
                            rgb_vis_params['max'] = [rgb_vis_params['max']] * 3 if not isinstance(rgb_vis_params['max'], list) else rgb_vis_params['max']
                        else:
                            # Use 255 as the default max for RGB visualization (common for 8-bit imagery like Landsat)
                            rgb_vis_params['max'] = [255, 255, 255]
                        
                        logger.info(f"Using RGB visualization with params: {rgb_vis_params}")
                        map_id_dict = image.getMapId(rgb_vis_params)
                    else:
                        map_id_dict = image.getMapId(vis_params)
                        
                    is_feature_collection = False
                except Exception as e:
                    logger.error(f"Error processing image: {str(e)}")
                    return jsonify({'error': f'Error processing image: {str(e)}'}), 500
                
            else:
                # Handle image collection
                logger.info(f"Processing ImageCollection: {gee_collection}")
                
                # Special handling for ESA WorldCover
                if 'ESA/WorldCover' in gee_collection:
                    logger.info("Detected ESA WorldCover dataset, applying special visualization")
                    
                    try:
                        image, updated_vis_params = handle_worldcover_visualization(gee_collection)
                        map_id_dict = image.getMapId(updated_vis_params)
                        is_feature_collection = False
                        
                        # Update palette for frontend (with # prefix)
                        palette = ['#' + color if not color.startswith('#') else color for color in updated_vis_params['palette']]
                        
                        # Also update min/max values for consistency
                        min_val = updated_vis_params.get('min', 0)
                        max_val = updated_vis_params.get('max', 11)
                    except Exception as e:
                        logger.error(f"Error processing WorldCover dataset: {str(e)}")
                        return jsonify({'error': f'Error processing WorldCover dataset: {str(e)}'}), 500
                
                # Special handling for Sentinel-1 SAR GRD data
                elif 'COPERNICUS/S1_GRD' in gee_collection:
                    logger.info("Detected Sentinel-1 dataset, applying special polarization filtering")
                    
                    try:
                        # Check if we have coordinates from the frontend
                        point = None
                        if 'coordinates' in data and 'lon' in data['coordinates'] and 'lat' in data['coordinates']:
                            lon = data['coordinates']['lon']
                            lat = data['coordinates']['lat']
                            logger.info(f"Using provided coordinates for Sentinel-1: {lon}, {lat}")
                            point = ee.Geometry.Point([lon, lat])
                        elif 'js_map_center' in data:
                            # Try to use map center coordinates
                            map_center = data['js_map_center']
                            if 'lon' in map_center and 'lat' in map_center:
                                lon = map_center['lon']
                                lat = map_center['lat']
                                logger.info(f"Using map center for Sentinel-1: {lon}, {lat}")
                                point = ee.Geometry.Point([lon, lat])
                        
                        image, updated_vis_params = handle_sentinel1_visualization(gee_collection, date_range, point)
                        map_id_dict = image.getMapId(updated_vis_params)
                        is_feature_collection = False
                        
                        # Update palette info for frontend
                        palette = ['#000000', '#0000FF', '#00FFFF', '#FFFF00', '#FF0000', '#FFFFFF']
                        
                        # Also update min/max values for consistency
                        min_val = updated_vis_params.get('min', -25)
                        max_val = updated_vis_params.get('max', 0)
                        
                        # Set the selected band for frontend display
                        bands = ['VV']  # Default to VV as that's our primary target
                        
                        logger.info(f"Successfully processed Sentinel-1 data with filtered polarization")
                    except Exception as e:
                        logger.error(f"Error processing Sentinel-1 dataset: {str(e)}")
                        return jsonify({'error': f'Error processing Sentinel-1 dataset: {str(e)}'}), 500
                
                # Special handling for Open Buildings Temporal dataset
                elif 'GOOGLE/Research/open-buildings-temporal/v1' in gee_collection:
                    logger.info("Detected Open Buildings Temporal dataset, applying special visualization")
                    
                    try:
                        # Check if we have coordinates from the frontend
                        point = None
                        if 'coordinates' in data and 'lon' in data['coordinates'] and 'lat' in data['coordinates']:
                            lon = data['coordinates']['lon']
                            lat = data['coordinates']['lat']
                            logger.info(f"Using provided coordinates for Open Buildings Temporal: {lon}, {lat}")
                            point = ee.Geometry.Point([lon, lat])
                        elif 'js_map_center' in data:
                            # Try to use map center coordinates
                            map_center = data['js_map_center']
                            if 'lon' in map_center and 'lat' in map_center:
                                lon = map_center['lon']
                                lat = map_center['lat']
                                logger.info(f"Using map center for Open Buildings Temporal: {lon}, {lat}")
                                point = ee.Geometry.Point([lon, lat])
                        elif dataset and 'js_visualization_info' in dataset and 'map_center' in dataset['js_visualization_info']:
                            # Try to use dataset's default map center
                            map_center = dataset['js_visualization_info']['map_center']
                            if 'lon' in map_center and 'lat' in map_center:
                                lon = map_center['lon']
                                lat = map_center['lat']
                                logger.info(f"Using dataset default map center for Open Buildings Temporal: {lon}, {lat}")
                                point = ee.Geometry.Point([lon, lat])
                        else:
                            # Use default point in New Cairo, Egypt
                            lon = 31.549876545106667
                            lat = 30.011531513347673
                            logger.info(f"Using default coordinates for Open Buildings Temporal: {lon}, {lat}")
                            point = ee.Geometry.Point([lon, lat])
                        
                        image, updated_vis_params = handle_open_buildings_temporal_visualization(gee_collection, point)
                        map_id_dict = image.getMapId(updated_vis_params)
                        is_feature_collection = False
                        
                        # Update palette for frontend (with # prefix)
                        palette = ['#000000', '#FFFFFF']  # Black to white
                        
                        # Also update min/max values for consistency
                        min_val = 0
                        max_val = 1
                    except Exception as e:
                        logger.error(f"Error processing Open Buildings Temporal dataset: {str(e)}")
                        return jsonify({'error': f'Error processing Open Buildings Temporal dataset: {str(e)}'}), 500
                
                # Process other image collections with temporal filter if provided
                else:
                    try:
                        collection = ee.ImageCollection(gee_collection).filterDate(date_range[0], date_range[1])
                        
                        # Check if we need to apply temporal aggregation (median)
                        aggregation_method = None
                        if 'temporal_filter' in vis_params:
                            aggregation_method = vis_params['temporal_filter'].get('aggregation')
                            logger.info(f"Using temporal aggregation method: {aggregation_method}")
                        
                        # Apply appropriate aggregation method
                        if aggregation_method == 'median':
                            logger.info(f"Computing median mosaic for date range: {date_range}")
                            image = collection.median()
                        elif aggregation_method == 'mean':
                            logger.info(f"Computing mean mosaic for date range: {date_range}")
                            image = collection.mean()
                        elif is_time_series:
                            # For time series datasets, use the most recent image
                            logger.info(f"Using most recent image from date range: {date_range}")
                            image = collection.sort('system:time_start', False).first()
                        elif is_landsat_sentinel:
                            # For Landsat/Sentinel, create a median mosaic
                            logger.info(f"Creating median mosaic for Landsat/Sentinel from date range: {date_range}")
                            image = collection.median()
                        else:
                            # Default approach: use mosaic
                            logger.info(f"Using default mosaic method")
                            image = collection.mosaic()
                        
                        # For custom band visualization, select the specific band if provided
                        if visualization and 'band' in visualization:
                            selected_band = visualization.get('band')
                            logger.info(f"Selecting specific band for visualization: {selected_band}")
                            
                            # Select only the requested band
                            if isinstance(selected_band, str):
                                image = image.select(selected_band)
                                logger.info(f"Visualizing single band: {selected_band}")
                        
                        map_id_dict = image.getMapId(vis_params)
                        is_feature_collection = False
                    except Exception as e:
                        logger.error(f"Error processing image collection: {str(e)}")
                        return jsonify({'error': f'Error processing image collection: {str(e)}'}), 500
            
            # Get the tile URL
            tile_url = map_id_dict['tile_fetcher'].url_format
            logger.info(f"Generated tile URL: {tile_url}")
            
            # Get feature properties if this is a feature collection
            feature_properties = []
            if is_feature_collection and 'features' in locals():
                feature_properties = get_feature_properties(features, gee_collection)
            
            # For RGB datasets with 3 bands, use 0-255 range
            min_val = vis_params.get('min', 0)
            max_val = vis_params.get('max', 255)
            
            # Return all needed information
            response_data = {
                'tileUrl': tile_url, 
                'bands': bands, 
                'palette': palette,
                'min': min_val,
                'max': max_val,
                'bbox': bbox,
                'class_descriptions': class_descriptions,
                'lookat': lookat,
                'is_feature_collection': is_feature_collection,
                'feature_properties': feature_properties,
                'date_range': date_range  # Include date range in the response
            }
            
            # Add js_map_center if it's available as a dictionary
            if isinstance(dataset.get('js_visualization_info', None), dict) and 'map_center' in dataset['js_visualization_info']:
                response_data['js_map_center'] = dataset['js_visualization_info']['map_center']

            if 'palette' in response_data and response_data['palette']:
                    processed_palette = []
                    for color in response_data['palette']:
                        if isinstance(color, str):
                            # Add # prefix if it's a hex code without one
                            if color.lower().startswith('0x'):
                                # Handle 0x prefix
                                processed_palette.append('#' + color[2:])
                            elif re.match(r'^[0-9a-fA-F]{6}$', color):
                                processed_palette.append('#' + color)
                            else:
                                processed_palette.append(color)

 
                    response_data['palette'] = processed_palette
                    logger.info(f"Processed palette for frontend: {processed_palette}")
                
            # Ensure class_descriptions have color values with # prefix
            if 'class_descriptions' in response_data and response_data['class_descriptions']:
                for cls in response_data['class_descriptions']:
                    if 'color' in cls and isinstance(cls['color'], str) and not cls['color'].startswith('#'):
                        # Add # prefix to color values
                        cls['color'] = '#' + cls['color']
                
                logger.info(f"Processed class_descriptions for frontend")
            
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error in get_tile: {str(e)}")
            return jsonify({'error': str(e)}), 500

def register_value_retrieval_route(app,embedding_manager):
    """Register route for retrieving values at specific locations"""
    
    @app.route('/get_value_at_location', methods=['POST'])
    def get_value_at_location():
        data = request.get_json()
        
        # Get required parameters
        dataset_id = data.get('dataset_id')
        #dataset_id = dataset_id.replace('/', '_') if '/' in dataset_id else dataset_id
        coordinates = data.get('coordinates', {})
        lat = coordinates.get('lat')
        lon = coordinates.get('lon')
        
        if not dataset_id or lat is None or lon is None:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        try:
            # Create a point at the specified location
            point = ee.Geometry.Point([lon, lat])
            
            # Get temporal filter if provided
            temporal_filter = data.get('temporal_filter')
            visualization_params = data.get('visualization')
            
            # Try to find dataset metadata if available from our embedding manager
            dataset = None
            if hasattr(embedding_manager, 'datasets') and embedding_manager.datasets:
                dataset = next((embedding_manager.datasets[d] for d in embedding_manager.datasets if embedding_manager.datasets[d]['id'] == dataset_id), None)
            
            # Determine appropriate scale for sampling based on dataset type
            sampling_scale = get_best_scale_for_dataset(dataset_id)
            logger.info(f"Using sampling scale of {sampling_scale}m for dataset {dataset_id}")
            
            # Try to determine the type of the dataset
            dataset_type = 'unknown'
            
            # Check for explicit type info in the dataset
            if dataset and 'gee:type' in dataset:
                dataset_type = dataset['gee:type'].lower()
            # Or try to infer from the ID
            elif any(x in dataset_id for x in ['ImageCollection', 'COPERNICUS', 'LANDSAT', 'MODIS', 'VIIRS']):
                dataset_type = 'image_collection'
            elif 'Table' in dataset_id or 'FeatureCollection' in dataset_id:
                dataset_type = 'feature_collection'
            elif 'Image' in dataset_id or 'DEM' in dataset_id:
                dataset_type = 'image'
            
            logger.info(f"Processing value retrieval for dataset_id: {dataset_id}, type: {dataset_type}")
            
            # Handle based on determined type
            if dataset_type == 'image_collection' or dataset_type == 'imagecollection':
                # For image collections (Sentinel, Landsat, MODIS, etc.)
                collection = ee.ImageCollection(dataset_id)
                
                # Apply temporal filtering with our enhanced function
                filtered_collection, date_range, aggregation_method = apply_temporal_filter_to_collection(
                    collection, 
                    temporal_filter,
                    dataset
                )
                
                # Override aggregation method if specified in the request
                if temporal_filter and 'aggregation' in temporal_filter:
                    aggregation_method = temporal_filter['aggregation']
                
                # Get an appropriate image using our enhanced function
                image = get_image_from_collection(
                    filtered_collection,
                    date_range,
                    aggregation_method,
                    dataset_id
                )
                
                # Get the timestamp if available
                date_millis = None
                try:
                    date_millis = image.get('system:time_start').getInfo()
                except:
                    # For aggregated images, try to get date range
                    if date_range:
                        date_str = f"{date_range[0]} to {date_range[1]}"
                        logger.info(f"Using date range for aggregated image: {date_str}")
                        return jsonify({
                            'values': sample_image_values(image, point, sampling_scale),
                            'date': date_str
                        })
                    else:
                        logger.warning(f"No timestamp available for {dataset_id}")
                
                date_str = None
                if date_millis:
                    date_obj = datetime.fromtimestamp(date_millis / 1000)
                    date_str = date_obj.strftime('%Y-%m-%d')
                
                # Handle specific band selection if provided
                if visualization_params and 'band' in visualization_params:
                    selected_band = visualization_params['band']
                    logger.info(f"Selecting specific band for value retrieval: {selected_band}")
                    try:
                        image = image.select(selected_band)
                    except Exception as e:
                        logger.warning(f"Failed to select band {selected_band}: {str(e)}")
                elif data.get('band'):
                    selected_band = data.get('band')
                    logger.info(f"Selecting specific band from request: {selected_band}")
                    try:
                        image = image.select(selected_band)
                    except Exception as e:
                        logger.warning(f"Failed to select band {selected_band}: {str(e)}")
                
                # Sample the image at the specified point with progressive scales
                values = sample_image_values(image, point, sampling_scale)
                
                return jsonify({
                    'values': values,
                    'date': date_str,
                    'aggregation': aggregation_method
                })
            
            elif dataset_type == 'feature_collection' or dataset_type == 'table':
                # For feature collections (boundaries, etc.)
                features = ee.FeatureCollection(dataset_id)
                
                # Filter to features that intersect the point
                filtered = features.filterBounds(point)
                
                # Get the first 5 features to avoid overwhelming responses
                features_info = filtered.limit(5).getInfo()
                
                if features_info and 'features' in features_info and len(features_info['features']) > 0:
                    return jsonify({
                        'features': features_info['features']
                    })
                else:
                    return jsonify({'error': 'No features found at this location'})
            
            elif dataset_type == 'image':
                # For single images (DEMs, land cover, etc.)
                image = ee.Image(dataset_id)
                
                # Sample at point using progressive scales
                values = sample_image_values(image, point, sampling_scale)
                
                return jsonify({
                    'values': values
                })
            
            else:
                # If type is unknown, try all approaches
                logger.info(f"Trying multiple approaches for dataset of unknown type: {dataset_id}")
                
                # First priority: Try as image collection with temporal filter
                try:
                    collection = ee.ImageCollection(dataset_id)
                    
                    # Apply temporal filtering
                    filtered_collection, date_range, aggregation_method = apply_temporal_filter_to_collection(
                        collection, 
                        temporal_filter,
                        dataset
                    )
                    
                    # Get appropriate image
                    image = get_image_from_collection(
                        filtered_collection,
                        date_range,
                        aggregation_method,
                        dataset_id
                    )
                    
                    # Sample values
                    values = sample_image_values(image, point, sampling_scale)
                    
                    if values and any(v is not None for v in values.values()):
                        # Get date information if possible
                        date_str = None
                        try:
                            date_millis = image.get('system:time_start').getInfo()
                            if date_millis:
                                date_obj = datetime.fromtimestamp(date_millis / 1000)
                                date_str = date_obj.strftime('%Y-%m-%d')
                        except:
                            # Use date range for aggregated images
                            if date_range:
                                date_str = f"{date_range[0]} to {date_range[1]}"
                        
                        return jsonify({
                            'values': values,
                            'date': date_str
                        })
                except Exception as e:
                    logger.info(f"Image collection approach failed: {str(e)}")
                
                # Second priority: Try as single image
                try:
                    image = ee.Image(dataset_id)
                    values = sample_image_values(image, point, sampling_scale)
                    
                    if values and any(v is not None for v in values.values()):
                        return jsonify({
                            'values': values
                        })
                except Exception as e:
                    logger.info(f"Single image approach failed: {str(e)}")
                
                # Third priority: Try as feature collection
                try:
                    features = ee.FeatureCollection(dataset_id)
                    filtered = features.filterBounds(point)
                    features_info = filtered.limit(5).getInfo()
                    
                    if features_info and 'features' in features_info and len(features_info['features']) > 0:
                        return jsonify({
                            'features': features_info['features']
                        })
                except Exception as e:
                    logger.info(f"Feature collection approach failed: {str(e)}")
                
                # If all approaches failed
                return jsonify({'error': 'Could not determine dataset type or find values at this location'})
                    
        except Exception as e:
            logger.error(f"Error getting value at location: {str(e)}")
            return jsonify({'error': f'Error: {str(e)}'})

    # Helper function to sample image values with progressive scales
    def sample_image_values(image, point, scale=30):
        """Sample image values at a point using progressively larger scales if needed"""
        logger = logging.getLogger(__name__)
        
        # Try with initial scale
        try:
            values = image.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=scale
            ).getInfo()
            
            # If we got non-null values, return them
            if values and any(v is not None for v in values.values()):
                return values
                
            # Otherwise try with progressively larger scales
            for larger_scale in [scale*2, scale*5, 500, 1000]:
                logger.info(f"No values found at scale={scale}, trying with scale={larger_scale}")
                
                values = image.reduceRegion(
                    reducer=ee.Reducer.first(),
                    geometry=point,
                    scale=larger_scale
                ).getInfo()
                
                if values and any(v is not None for v in values.values()):
                    return values
                    
            # If all attempts failed, return whatever we have
            return values or {}
            
        except Exception as e:
            logger.error(f"Error sampling image: {str(e)}")
            return {}