"""
Main entry point for the GIS AI Agent.

This module initializes and starts the MCP server and handles the main application flow.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import asyncio
import argparse
import signal
from pathlib import Path
import traceback

# Add the parent directory to the sys.path to allow importing from other modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.mcp_server.server import create_server
from src.mcp_server.health import register_health_routes
from src.utils.cache import schedule_cache_maintenance


def setup_logging(debug_mode=False):
    """Configure application logging with rotating file handler"""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler for development/debugging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation for production use
    file_handler = RotatingFileHandler(
        log_dir / "gis_agent.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Reduce logging level for some noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    return root_logger


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="GIS AI Agent - A powerful GIS and sustainability analysis tool")
    
    parser.add_argument(
        "--config-dir",
        help="Path to configuration directory",
        default=None
    )
    
    parser.add_argument(
        "--host",
        help="Server host address",
        default=None
    )
    
    parser.add_argument(
        "--port",
        type=int,
        help="Server port",
        default=None
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    return parser.parse_args()


def setup_signal_handlers(server, logger):
    """Set up signal handlers for graceful shutdown."""
    
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, shutting down gracefully")
        # Set a flag to stop accepting new connections
        if hasattr(server, 'should_exit'):
            server.should_exit = True
        # Give tasks a chance to complete
        logger.info("Allowing running tasks to complete")
        asyncio.get_event_loop().stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


async def cleanup_resources():
    """Clean up resources before shutdown."""
    logger = logging.getLogger(__name__)
    logger.info("Cleaning up resources...")
    
    # Close any database connections or external clients
    # For example, disconnect from Firebase or other services
    
    # Ensure all temporary files are deleted
    temp_dir = Path("data/temp")
    if temp_dir.exists():
        try:
            for temp_file in temp_dir.glob("*"):
                if temp_file.is_file():
                    temp_file.unlink()
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")
    
    logger.info("Resource cleanup completed")


async def async_main(args):
    """
    Asynchronous main function that starts the MCP server.

    Args:
        args: Command-line arguments.
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get configuration
        config = get_config()
        
        # Create the MCP server
        server = create_server(name="GIS AI Agent")
        
        # Override configuration with command-line arguments and environment variables
        server_config = config.get_server_config().get("server", {})
        
        if args.host is not None:
            server.host = args.host
        
        if args.port is not None:
            server.port = args.port
        elif "PORT" in os.environ:
            try:
                server.port = int(os.environ["PORT"])
                logger.info(f"Using port from environment variable: {server.port}")
            except ValueError:
                logger.warning(f"Invalid PORT environment variable: {os.environ['PORT']}")
        
        if args.debug:
            server.debug = True
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Register health check endpoints
        register_health_routes(server.app)
        
        # Set up signal handlers for graceful shutdown
        setup_signal_handlers(server, logger)
        
        # Schedule cache maintenance
        schedule_cache_maintenance()
        
        # Log server configuration
        logger.info(f"Starting GIS AI Agent server at {server.host}:{server.port}")
        if server.debug:
            logger.info("Debug mode enabled")
        
        # Run the server asynchronously
        await server.run()
    
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        await cleanup_resources()
    except Exception as e:
        logger.critical(f"Fatal error starting server: {e}")
        logger.critical(traceback.format_exc())
        await cleanup_resources()
        sys.exit(1)
    finally:
        # Ensure cleanup happens
        await cleanup_resources()


def main():
    """Main entry point for the application."""
    args = parse_arguments()
    
    # Setup logging based on debug argument
    logger = setup_logging(args.debug)
    
    try:
        # Print banner only in debug mode
        if args.debug:
            print("""
 ██████╗ ██╗███████╗     █████╗ ██╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔════╝ ██║██╔════╝    ██╔══██╗██║    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
██║  ███╗██║███████╗    ███████║██║    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
██║   ██║██║╚════██║    ██╔══██║██║    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
╚██████╔╝██║███████║    ██║  ██║██║    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
 ╚═════╝ ╚═╝╚══════╝    ╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
                                                                                     
            """)
            print("GIS AI Agent - A powerful GIS and sustainability analysis tool")
            print("-----------------------------------------------------------")
        else:
            logger.info("GIS AI Agent starting in production mode")
        
        # Create necessary directories
        Path("data/cache").mkdir(parents=True, exist_ok=True)
        Path("data/temp").mkdir(parents=True, exist_ok=True)
        
        # Run the async main function
        asyncio.run(async_main(args))
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)


# Global app variable for ASGI servers (Gunicorn, etc.)
app = None

# Initialize the application for ASGI servers
def init_app():
    """Initialize the application for ASGI servers like Gunicorn."""
    global app
    
    if app is None:
        try:
            # Setup logging
            setup_logging(os.environ.get("DEBUG", "false").lower() == "true")
            
            # Get configuration
            config = get_config()
            
            # Create the server
            server = create_server(name="GIS AI Agent")
            
            # Configure port from environment variable for Cloud Run
            if "PORT" in os.environ:
                try:
                    server.port = int(os.environ["PORT"])
                    logging.info(f"Using port from environment variable: {server.port}")
                except ValueError:
                    logging.warning(f"Invalid PORT environment variable: {os.environ['PORT']}")
            
            # Register health check endpoints
            register_health_routes(server.app)
            
            # Schedule cache maintenance
            schedule_cache_maintenance()
            
            # Set the global app
            app = server.app
        
        except Exception as e:
            logging.critical(f"Failed to initialize application: {e}")
            logging.critical(traceback.format_exc())
            raise
    
    return app


if __name__ == "__main__":
    main()
else:
    # When imported by ASGI servers
    app = init_app() 