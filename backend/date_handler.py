import re
import datetime
import logging
from typing import Tuple, Optional, Union, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DateHandler:
    """
    Universal date handler for Earth Engine applications.
    Processes various date formats and returns standardized date ranges for EE functions.
    """
    
    def __init__(self):
        self.month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
    
    def parse_date_input(self, date_input: Union[str, int, None]) -> Union[str, None]:
        """
        Parse various date formats and return a standardized YYYY-MM-DD string.
        
        Args:
            date_input: Date in various formats (string/int/None)
        
        Returns:
            Standardized date string in YYYY-MM-DD format or None
        """
        if date_input is None:
            return None
            
        # Handle "latest" keyword
        if isinstance(date_input, str) and "latest" in date_input.lower():
            return "latest"
            
        # Handle year as integer
        if isinstance(date_input, int):
            return f"{date_input}-01-01"
            
        # Handle year-only input (e.g., "2022")
        if isinstance(date_input, str) and re.match(r'^\d{4}$', date_input):
            return f"{date_input}-01-01"
            
        # Handle full date that's already formatted (YYYY-MM-DD)
        if isinstance(date_input, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', date_input):
            return date_input
            
        # Month-year patterns
        month_patterns = {
            r'(\w+)\s+(\d{4})': lambda m: f"{m.group(2)}-{self._get_month_number(m.group(1)):02d}-01",  # March 2022
            r'(\d{1,2})[/-](\d{4})': lambda m: f"{m.group(2)}-{int(m.group(1)):02d}-01",          # 03/2022 or 03-2022
            r'(\d{4})[/-](\d{1,2})': lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-01"           # 2022/03 or 2022-03
        }
        
        if isinstance(date_input, str):
            for pattern, formatter in month_patterns.items():
                match = re.match(pattern, date_input)
                if match:
                    return formatter(match)
        
        # If none of the patterns match, return as is
        return date_input
    
    def _get_month_number(self, month_name: str) -> int:
        """
        Convert month name to number.
        
        Args:
            month_name: String representation of month (e.g., "January")
            
        Returns:
            Month number (1-12)
        """
        return self.month_names.get(month_name.lower(), 1)
    
    def extract_month_from_prompt(self, prompt: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract month and year from a prompt string.
        
        Args:
            prompt: User input string
            
        Returns:
            Tuple of (month, year) or (None, None) if not found
        """
        if not isinstance(prompt, str):
            return None, None
            
        # Try month name + year pattern (e.g., "April 2022")
        month_year_pattern = r'(?i)(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{4})'
        match = re.search(month_year_pattern, prompt)
        if match:
            month_name = match.group(1).lower()
            year = int(match.group(2))
            month = self._get_month_number(month_name)
            return month, year
            
        # Try numeric patterns (e.g., "04/2022" or "2022-04")
        numeric_patterns = [
            r'(\d{1,2})[/-](\d{4})',  # 04/2022
            r'(\d{4})[/-](\d{1,2})'   # 2022-04 or 2022/04
        ]
        
        for pattern in numeric_patterns:
            match = re.search(pattern, prompt)
            if match:
                if match.group(1).isdigit() and int(match.group(1)) <= 12:
                    # Pattern is MM/YYYY
                    month = int(match.group(1))
                    year = int(match.group(2))
                else:
                    # Pattern is YYYY/MM
                    year = int(match.group(1))
                    month = int(match.group(2))
                return month, year
                
        return None, None
    
    def get_date_range(self, start_date: Union[str, None], end_date: Union[str, None], 
                       year: Optional[int] = None, month: Optional[int] = None) -> Tuple[str, str]:
        """
        Process start_date and end_date to handle various formats and return a normalized range.
        
        Args:
            start_date: Start date string
            end_date: End date string
            year: Year integer (used if start_date and end_date are None)
            month: Month integer (used with year if start_date and end_date are None)
            
        Returns:
            Tuple of (start_date_str, end_date_str) in YYYY-MM-DD format
        """
        today = datetime.date.today()
        
        # If we have a year but no dates, create date range for that year
        if start_date is None and end_date is None and year is not None:
            if month is not None:
                # If we have both year and month, create range for that specific month
                start_date = f"{year}-{month:02d}-01"
                # Calculate the last day of the month
                if month == 12:
                    next_month_year = year + 1
                    next_month = 1
                else:
                    next_month_year = year
                    next_month = month + 1
                
                # Last day = one day before the first day of next month
                end_date = (datetime.datetime(next_month_year, next_month, 1) - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                logging.info(f"Created date range for {year}-{month:02d}: {start_date} to {end_date}")
            else:
                # If we have year but no month, create range for the whole year
                start_date = f"{year}-01-01"
                end_date = f"{year}-12-31"
                logging.info(f"Created date range for year {year}: {start_date} to {end_date}")
            return start_date, end_date
        
        # Process start date
        start_date = self.parse_date_input(start_date)
        
        # Handle "latest" case
        if start_date == "latest":
            return "latest", "latest"
        
        # Default start date if not provided
        if start_date is None:
            start_date = (today - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Process end date
        end_date = self.parse_date_input(end_date)
        
        # Default end date if not provided
        if end_date is None:
            # If start date is a year-only input that was converted to YYYY-01-01
            if start_date and re.match(r'^\d{4}-01-01$', start_date):
                # Set end date to the end of that year
                year = start_date[:4]
                end_date = f"{year}-12-31"
            # If start date is a month-year input that was converted to YYYY-MM-01
            elif start_date and re.match(r'^\d{4}-\d{2}-01$', start_date):
                # Set end date to the end of that month
                year = int(start_date[:4])
                month = int(start_date[5:7])
                
                # Get the last day of the month
                if month == 12:
                    next_month_year = year + 1
                    next_month = 1
                else:
                    next_month_year = year
                    next_month = month + 1
                
                # Last day = one day before the first day of next month
                end_date = (datetime.datetime(next_month_year, next_month, 1) - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                end_date = today.strftime('%Y-%m-%d')
        
        logging.info(f"Normalized date range: {start_date} to {end_date}")
        return start_date, end_date
    
    def generate_ee_date_filter(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Generate a dictionary of parameters suitable for Earth Engine date filtering.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary with date parameters in EE-compatible format
        """
        result = {}
        
        # Handle "latest" case
        if start_date == "latest" and end_date == "latest":
            today = datetime.date.today()
            search_start = (today - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
            search_end = today.strftime('%Y-%m-%d')
            
            result = {
                "date_type": "latest",
                "search_start": search_start,
                "search_end": search_end
            }
        else:
            result = {
                "date_type": "range",
                "start_date": start_date,
                "end_date": end_date
            }
            
            # Extract year information
            if start_date:
                year_match = re.match(r'^(\d{4})', start_date)
                if year_match:
                    result["year"] = int(year_match.group(1))
                
        return result

# Create a singleton instance
date_handler = DateHandler()