// src/components/Layout/TopBar.jsx
import PropTypes from 'prop-types';
// Import LayoutGrid icon (or choose another like Database, Library)
import { Settings, HelpCircle, Info, LayoutGrid } from 'lucide-react'; // Ensure LayoutGrid is imported
import ProfileMenu from '../UI/ProfileMenu';

const TopBar = ({ showNotification }) => {
  return (
    // Using Tailwind classes directly based on previous examples
    <div className="h-12 w-full bg-google-bg border-b border-google-bg-light/10 flex items-center justify-between px-4 z-20 fixed top-0 left-0 right-0">

      {/* Left side - Logo */}
      <div className="flex items-center">
        <img
          src="/geolong.png" // Make sure this path is correct
          alt="GeoGemma Logo"
          className="w-32 object-contain mr-1" // Reduced width and margin
        />
      </div>

      {/* Right side - Actions */}
      <div className="flex items-center space-x-1"> {/* Adjust space if needed */}

        {/* --- NEW Dataset Explorer Button --- */}
        <button>
        <a
        href="http://127.0.0.1:5000/"
        target="_blank"
        rel="noopener noreferrer"
        className="px-4 py-1.5 bg-google-bg-light/70 text-white font-medium rounded-md hover:bg-google-bg-light/90 transition-colors border border-google-bg-light/30"
        title="Open Dataset Explorer"
        style={{ borderRadius: '10px' }}
      >
        Dataset Explorer
      </a>
        </button>
        {/* --- END NEW Button --- */}

        {/* Existing Info Button */}
        <button
          className="p-1.5 text-google-grey-300 hover:text-white rounded-full hover:bg-google-bg-light/40 transition-colors"
          onClick={() => showNotification('GeoGemma - A Google Research Project', 'info')}
          title="About"
        >
          <Info size={18} />
        </button>

        {/* Existing ProfileMenu component */}
        <ProfileMenu />
      </div>
    </div>
  );
};

TopBar.propTypes = {
  showNotification: PropTypes.func.isRequired
};

export default TopBar;