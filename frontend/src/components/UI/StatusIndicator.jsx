// src/components/UI/StatusIndicator.jsx
import PropTypes from 'prop-types';

const StatusIndicator = ({ message = 'Processing...' }) => {
  return (
    <div className="fixed top-14 left-1/2 transform -translate-x-1/2 bg-google-bg-light text-google-grey-100 px-4 py-3 rounded-lg z-50 shadow-md flex items-center">
      {/* Google-style loading spinner */}
      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-google-blue" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span className="font-medium">{message}</span>
    </div>
  );
};

StatusIndicator.propTypes = {
  message: PropTypes.string
};

export default StatusIndicator;