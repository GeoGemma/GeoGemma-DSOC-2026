// src/components/UI/ProfileMenu.jsx
import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, Settings, HelpCircle, Download, ChevronRight, Info } from 'lucide-react';
import '../../styles/profileMenu.css';

const ProfileMenu = () => {
  const { currentUser, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  
  // Get user initials for avatar display
  const getUserInitials = () => {
    if (!currentUser || !currentUser.displayName) return "U";
    const names = currentUser.displayName.split(' ');
    if (names.length === 1) return names[0].charAt(0);
    return names[0].charAt(0) + names[names.length - 1].charAt(0);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      setIsOpen(false);
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  // Show about notification
  const handleAbout = () => {
    if (window && window.dispatchEvent) {
      window.dispatchEvent(new CustomEvent('notification', {
        detail: {
          message: 'GeoGemma - A Google Research Project',
          type: 'info',
          duration: 4000
        }
      }));
    } else {
      alert('GeoGemma - A Google Research Project');
    }
  };

  // Don't render anything if not logged in
  if (!currentUser) return null;

  return (
    <div className="profile-menu-container" ref={menuRef}>
      <button 
        className="profile-icon-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="User profile"
      >
        {currentUser.photoURL ? (
          <img 
            src={currentUser.photoURL} 
            alt="Profile" 
            className="profile-avatar"
          />
        ) : (
          <div className="profile-avatar-initials">
            {getUserInitials()}
          </div>
        )}
      </button>
      
      {isOpen && (
        <div className="profile-dropdown scale-in">
          <div className="profile-header">
            <div className="profile-info">
              {currentUser.photoURL ? (
                <img 
                  src={currentUser.photoURL} 
                  alt="Profile" 
                  className="profile-image"
                />
              ) : (
                <div className="profile-initials">
                  {getUserInitials()}
                </div>
              )}
              <div className="profile-text">
                <div className="profile-name">{currentUser.displayName || 'User'}</div>
                <div className="profile-email">{currentUser.email}</div>
              </div>
            </div>
          </div>
          
          <div className="profile-menu-items">
            <button className="profile-menu-item">
              <Settings size={18} />
              <span>Settings</span>
            </button>
            
            <button className="profile-menu-item">
              <HelpCircle size={18} />
              <span>Help</span>
            </button>
            
            <button className="profile-menu-item">
              <Download size={18} />
              <span>Download data</span>
              <ChevronRight size={16} className="menu-item-arrow" />
            </button>
            
            <button className="profile-menu-item" onClick={handleAbout}>
              <Info size={18} />
              <span>About</span>
            </button>
            
            <div className="profile-divider"></div>
            
            <button className="profile-menu-item" onClick={handleLogout}>
              <LogOut size={18} />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfileMenu;