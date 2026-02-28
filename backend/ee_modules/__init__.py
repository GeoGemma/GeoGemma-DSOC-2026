# __init__.py (ee_modules) -  It correctly defines the package.
from . import rgb
from . import ndvi
from . import water
from . import lulc
from . import lst
from . import openbuildings
from . import forest_change
from . import SAR
from . import active_fire
from . import gases
__all__ = ["rgb", "ndvi", "water", "lulc", "lst", "openbuildings","forest_change", 'SAR', 'active_fire', 'gases']
