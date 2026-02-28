from flask import render_template
import logging

logger = logging.getLogger(__name__)

def register_main_routes(app):
    """Register main application routes"""
    
    @app.route('/')
    def index():
        return render_template('index.html')
